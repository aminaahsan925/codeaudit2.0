"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useCallback, useEffect } from "react";

import {
  demoLogin,
  getMe,
  getProviders,
  logout,
  type ApiError,
  type MeResponse,
  type ProvidersResponse,
  type SessionResponse,
} from "@/lib/api";
import { notifySessionChanged, SESSION_CHANGED_EVENT } from "@/lib/session";

export const providersQueryKey = ["auth", "providers"] as const;
export const meQueryKey = ["auth", "me"] as const;

/** Which sign-in options the backend currently offers. */
export function useProviders() {
  return useQuery<ProvidersResponse, ApiError>({
    queryKey: providersQueryKey,
    queryFn: ({ signal }) => getProviders({ signal }),
    staleTime: 5 * 60_000,
  });
}

/**
 * The signed-in user, or null for a guest. The session lives in an HttpOnly
 * cookie, so this query always runs: a 401 just means nobody is signed in.
 * Sign-in and sign-out invalidate the query, so the header follows at once.
 */
export function useAuth() {
  const queryClient = useQueryClient();
  const query = useQuery<MeResponse, ApiError>({
    queryKey: meQueryKey,
    queryFn: ({ signal }) => getMe({ signal }),
    retry: false,
    staleTime: 5 * 60_000,
  });

  useEffect(() => {
    const refresh = () => {
      void queryClient.invalidateQueries({ queryKey: meQueryKey });
    };
    window.addEventListener(SESSION_CHANGED_EVENT, refresh);
    return () => window.removeEventListener(SESSION_CHANGED_EVENT, refresh);
  }, [queryClient]);

  return {
    user: query.data ?? null,
    isSignedIn: query.isSuccess,
    isLoading: query.isPending,
  };
}

/** Signs in the clearly-labelled local demo user. */
export function useDemoLogin() {
  const queryClient = useQueryClient();
  return useMutation<SessionResponse, ApiError, void>({
    mutationFn: () => demoLogin(),
    onSuccess: () => {
      notifySessionChanged();
      void queryClient.invalidateQueries({ queryKey: meQueryKey });
    },
  });
}

/** Signs out: tells the backend (which clears the session cookie), goes home. */
export function useSignOut() {
  const queryClient = useQueryClient();
  const router = useRouter();
  return useCallback(async () => {
    try {
      await logout();
    } catch {
      // Signing out locally regardless; the cookie is cleared either way.
    }
    notifySessionChanged();
    queryClient.removeQueries({ queryKey: meQueryKey });
    router.replace("/");
  }, [queryClient, router]);
}
