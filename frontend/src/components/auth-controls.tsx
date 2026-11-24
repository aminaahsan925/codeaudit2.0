"use client";

import { useAuth, useProviders, useSignOut } from "@/hooks/use-auth";
import { googleLoginUrl } from "@/lib/api";

import { ButtonLink } from "./button-link";
import { Button } from "./ui/button";
import { Skeleton } from "./ui/skeleton";

function initialsFor(
  name: string | null | undefined,
  email: string | null | undefined,
): string {
  const source = (name ?? email ?? "?").trim();
  return source.charAt(0).toUpperCase();
}

/**
 * Header auth state: the signed-in user's picture and name with a sign-out
 * button, or a compact sign-in link when signed out. Demo users get a
 * visible "Demo" label so the account is never mistaken for a real one.
 */
export function AuthControls() {
  const { user, isSignedIn, isLoading } = useAuth();
  const providers = useProviders();
  const signOut = useSignOut();

  if (isLoading) {
    return (
      <div className="flex items-center gap-2" aria-hidden="true">
        <Skeleton className="size-8 rounded-full" />
        <Skeleton className="hidden h-4 w-24 sm:block" />
      </div>
    );
  }

  if (isSignedIn && user) {
    return (
      <div className="flex items-center gap-2">
        {user.picture_url ? (
          /* Plain img: the avatar is an external Google URL, and next/image
             cannot optimize remote pictures without remote-pattern config. */
          /* eslint-disable-next-line @next/next/no-img-element */
          <img
            src={user.picture_url}
            alt=""
            referrerPolicy="no-referrer"
            className="size-8 rounded-full object-cover"
          />
        ) : (
          <span
            aria-hidden="true"
            className="flex size-8 items-center justify-center rounded-full bg-muted text-sm font-medium"
          >
            {initialsFor(user.name, user.email)}
          </span>
        )}
        <span className="hidden max-w-40 truncate text-sm font-medium sm:block">
          {user.name ?? user.email}
        </span>
        {user.demo ? (
          <span className="hidden rounded-full border border-border px-2 py-0.5 text-xs text-muted-foreground sm:block">
            Demo
          </span>
        ) : null}
        <Button variant="ghost" size="sm" onClick={() => void signOut()}>
          Sign out
        </Button>
      </div>
    );
  }

  if (providers.data?.google) {
    return (
      <ButtonLink href={googleLoginUrl()} variant="outline" size="sm">
        Sign in
      </ButtonLink>
    );
  }

  return null;
}
