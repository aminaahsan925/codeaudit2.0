import { ButtonLink } from "@/components/button-link";
import { SignInButton } from "@/components/sign-in-button";
import { LogoMark } from "@/components/wordmark";

/**
 * Sign-in card: the sign-in options the backend offers (Google, or the
 * labelled demo sign-in), plus continuing without an account.
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

      <div className="mt-8">
        {/* Google or demo sign-in, depending on what the backend offers. */}
        <SignInButton />
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
