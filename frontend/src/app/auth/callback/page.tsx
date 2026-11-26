"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { ButtonLink } from "@/components/button-link";
import { getMe } from "@/lib/api";

/**
 * Landing page for the backend's Google callback redirect. The session
 * token arrives as an HttpOnly cookie on that redirect, so this page only
 * has to ask the backend who is signed in: success goes home, a 401 means
 * the sign-in did not finish.
 */
export default function AuthCallbackPage() {
  const router = useRouter();
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getMe()
      .then(() => {
        if (!cancelled) router.replace("/");
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });
    return () => {
      cancelled = true;
    };
  }, [router]);

  if (failed) {
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
