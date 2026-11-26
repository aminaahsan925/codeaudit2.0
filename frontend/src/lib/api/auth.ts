import type { components } from "@/types/api";

import { env } from "@/lib/env";

import { apiClient, apiRequest, type RequestOptions } from "./client";

export type MeResponse = components["schemas"]["MeResponse"];
export type ProvidersResponse = components["schemas"]["ProvidersResponse"];
export type SessionResponse = components["schemas"]["SessionResponse"];
export type UserResponse = components["schemas"]["UserResponse"];

/** Full URL of the backend's Google login redirect (a browser navigation). */
export function googleLoginUrl(): string {
  return `${env.NEXT_PUBLIC_API_BASE_URL}/api/auth/google/login`;
}

/** Which sign-in options the backend currently offers. Public, no auth. */
export async function getProviders(
  options?: RequestOptions,
): Promise<ProvidersResponse> {
  return apiRequest(
    ({ signal }) => apiClient.GET("/api/auth/providers", { signal }),
    options,
  );
}

/** The signed-in user, or a 401 ApiError when anonymous. */
export async function getMe(options?: RequestOptions): Promise<MeResponse> {
  return apiRequest(
    ({ signal }) => apiClient.GET("/api/auth/me", { signal }),
    options,
  );
}

/**
 * Signs in the clearly-labelled local demo user. Only works while Google is
 * not configured; the backend returns 404 once it is.
 */
export async function demoLogin(
  options?: RequestOptions,
): Promise<SessionResponse> {
  return apiRequest(
    ({ signal }) => apiClient.POST("/api/auth/demo-login", { signal }),
    options,
  );
}

/** Tells the backend the session is done; the token is discarded client-side. */
export async function logout(options?: RequestOptions): Promise<void> {
  await apiRequest(
    ({ signal }) => apiClient.POST("/api/auth/logout", { signal }),
    options,
  );
}
