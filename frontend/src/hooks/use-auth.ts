"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

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
import {
  clearSessionToken,
  getSessionToken,
  SESSION_CHANGED_EVENT,
  setSessionToken,
} from "@/lib/session";

export const providersQueryKey = ["auth", "providers"] as const;
export const meQueryKey = ["auth", "me"] as const;

/**
 * The stored session token, reacting to sign-in and sign-out in this tab and
 * to storage events from other tabs. Starts null so the first render matches
 * the server, then reads the real value in an effect.
 */
export function useSessionToken(): string | null {
  const [token, setToken] = useState<string | null>(null);

  useEffect(() => {
    const refresh = () => setToken(getSessionToken());
    refresh();
    window.addEventListener(SESSION_CHANGED_EVENT, refresh);
    window.addEventListener("storage", refresh);
    return () => {
      window.removeEventListener(SESSION_CHANGED_EVENT, refresh);
      window.removeEventListener("storage", refresh);
    };
  }, []);

  return token;
}

/** Which sign-in options the backend currently offers. */
export function useProviders() {
  return useQuery<ProvidersResponse, ApiError>({
    queryKey: providersQueryKey,
    queryFn: ({ signal }) => getProviders({ signal }),
    staleTime: 5 * 60_000,
  });
}

/**
 * The signed-in user, or null for a guest. The query only runs while a token
 * is stored; a 401 clears the stored token, so an expired session signs the
 * user out instead of erroring forever.
 */
export function useAuth() {
  const token = useSessionToken();
  const query = useQuery<MeResponse, ApiError>({
    queryKey: meQueryKey,
    queryFn: ({ signal }) => getMe({ signal }),
    enabled: token !== null,
    retry: false,
    staleTime: 5 * 60_000,
  });

  useEffect(() => {
    if (token !== null && query.isError && query.error.status === 401) {
      clearSessionToken();
    }
  }, [token, query.isError, query.error]);

  return {
    user: query.data ?? null,
    isSignedIn: token !== null && query.isSuccess,
    isLoading: token !== null && query.isPending,
    token,
  };
}

/** Signs in the clearly-labelled local demo user and stores its session. */
export function useDemoLogin() {
  const queryClient = useQueryClient();
  return useMutation<SessionResponse, ApiError, void>({
    mutationFn: () => demoLogin(),
    onSuccess: (session) => {
      setSessionToken(session.token);
      void queryClient.invalidateQueries({ queryKey: meQueryKey });
    },
  });
}

/** Signs out: tells the backend, drops the stored token, goes home. */
export function useSignOut() {
  const queryClient = useQueryClient();
  const router = useRouter();
  return useCallback(async () => {
    try {
      await logout();
    } catch {
      // Signing out locally regardless; the token is discarded either way.
    }
    clearSessionToken();
    queryClient.removeQueries({ queryKey: meQueryKey });
    router.replace("/");
  }, [queryClient, router]);
}
