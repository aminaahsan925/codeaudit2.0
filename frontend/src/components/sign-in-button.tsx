"use client";

import { useAuth, useDemoLogin, useProviders } from "@/hooks/use-auth";
import { googleLoginUrl } from "@/lib/api";

import { ButtonLink } from "./button-link";
import { Button } from "./ui/button";

/**
 * Sign-in control for the home page. Shows "Sign in with Google" when the
 * backend has Google configured, otherwise the clearly-labelled demo
 * sign-in. Signing in is optional: guests can run audits without it.
 */
export function SignInButton() {
  const { user, isSignedIn } = useAuth();
  const providers = useProviders();
  const demoLogin = useDemoLogin();

  if (isSignedIn && user) {
    return (
      <p className="text-sm text-muted-foreground">
        Signed in as {user.name ?? user.email}
        {user.demo ? " (demo account)" : ""}
      </p>
    );
  }

  if (providers.isPending) {
    return (
      <Button variant="outline" size="lg" disabled aria-label="Sign in">
        Sign in
      </Button>
    );
  }

  if (providers.isError || !providers.data) {
    // Sign-in is optional: a failed providers check never blocks the page.
    return null;
  }

  if (providers.data.google) {
    return (
      <div className="flex flex-col items-start gap-2">
        <ButtonLink href={googleLoginUrl()} variant="outline" size="lg">
          Sign in with Google
        </ButtonLink>
        <p className="text-sm text-muted-foreground">
          Signing in saves your audits to your account. Guests can still run
          audits without signing in.
        </p>
      </div>
    );
  }

  if (providers.data.demo) {
    return (
      <div className="flex flex-col items-start gap-2">
        <Button
          variant="outline"
          size="lg"
          onClick={() => demoLogin.mutate()}
          disabled={demoLogin.isPending}
        >
          {demoLogin.isPending ? "Signing in..." : "Demo sign-in"}
        </Button>
        <p className="text-sm text-muted-foreground">
          Demo sign-in: try LaunchAudit without an account. Audits are saved
          under a shared demo account, not a Google account.
        </p>
        {demoLogin.isError ? (
          <p role="alert" className="text-sm text-destructive">
            {demoLogin.error.message}
          </p>
        ) : null}
      </div>
    );
  }

  return null;
}
