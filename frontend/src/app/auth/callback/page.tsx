"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect } from "react";

import { ButtonLink } from "@/components/button-link";
import { setSessionToken } from "@/lib/session";

/**
 * Landing page for the backend's Google callback redirect, which carries the
 * session token as a ?token= query param. Stores the token and sends the
 * user home; the replace drops the token from the URL bar. Rendered behind
 * Suspense because useSearchParams needs a boundary under cacheComponents.
 */
function CallbackCapture() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token");

  useEffect(() => {
    if (token) {
      setSessionToken(token);
      router.replace("/");
    }
  }, [router, token]);

  if (!token) {
    return (
      <div className="container-page flex flex-col items-start gap-4 py-16">
        <h1 className="text-2xl font-bold tracking-[-0.02em]">
          Sign-in did not finish
        </h1>
        <p className="max-w-prose text-muted-foreground">
          No session came back from the sign-in. Please try again.
        </p>
        <ButtonLink href="/" variant="outline">
          Back to the home page
        </ButtonLink>
      </div>
    );
  }

  return (
    <div className="container-page py-16">
      <p className="text-muted-foreground">Signing you in...</p>
    </div>
  );
}

export default function AuthCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="container-page py-16">
          <p className="text-muted-foreground">Signing you in...</p>
        </div>
      }
    >
      <CallbackCapture />
    </Suspense>
  );
}
