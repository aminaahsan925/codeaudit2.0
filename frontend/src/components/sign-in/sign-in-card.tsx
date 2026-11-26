import { ButtonLink } from "@/components/button-link";
import { buttonVariants } from "@/components/ui/button";
import { LogoMark } from "@/components/wordmark";
import { cn } from "@/lib/utils";

/** The Google "G", drawn in the current text colour. */
function GoogleMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false" className={className}>
      <path
        fill="currentColor"
        d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
      />
      <path
        fill="currentColor"
        d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
      />
      <path
        fill="currentColor"
        d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z"
      />
      <path
        fill="currentColor"
        d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
      />
    </svg>
  );
}

/**
 * Sign-in card. Google sign-in is not built yet, so its button is a
 * focusable placeholder that does nothing and says so. The working path is
 * to continue without an account.
 */
export function SignInCard() {
  return (
    <section
      aria-labelledby="sign-in-heading"
      className="flex w-full max-w-[26rem] flex-col rounded-2xl border border-border bg-card p-6 shadow-card sm:p-8"
    >
      <LogoMark className="size-8" />
      <h1 id="sign-in-heading" className="mt-6 text-3xl text-foreground">
        Sign in to LaunchAudit
      </h1>
      <p className="mt-2 text-base text-muted-foreground">
        An account keeps all your reports in one place.
      </p>

      <div className="mt-8 flex flex-col gap-2">
        <button
          type="button"
          aria-disabled="true"
          aria-describedby="google-soon"
          className={cn(
            buttonVariants({ variant: "outline", size: "lg" }),
            "w-full cursor-not-allowed text-muted-foreground hover:bg-background hover:text-muted-foreground active:not-aria-[haspopup]:translate-y-0 dark:hover:bg-input/30",
          )}
        >
          <GoogleMark className="size-4" />
          Continue with Google
        </button>
        <p id="google-soon" className="text-center text-[0.8125rem] text-muted-foreground">
          Google sign-in is coming soon.
        </p>
      </div>

      <div className="my-6 flex items-center gap-3 text-sm text-muted-foreground">
        <span aria-hidden="true" className="h-px flex-1 bg-border" />
        or
        <span aria-hidden="true" className="h-px flex-1 bg-border" />
      </div>

      <ButtonLink href="/audits/new" size="lg" className="w-full">
        Continue without an account
      </ButtonLink>
      <p className="mt-3 text-[0.8125rem] text-muted-foreground">
        Without an account, you open each report from its link. Keep the link safe.
      </p>
    </section>
  );
}
