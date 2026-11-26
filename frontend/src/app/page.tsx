import { ButtonLink } from "@/components/button-link";
import { SampleReport } from "@/components/sample-report";
import { SignInButton } from "@/components/sign-in-button";

const STEPS = [
  {
    title: "Add your code",
    body: "Connect a GitHub repo or upload a zip. LaunchAudit reads the code; it never installs or runs it.",
  },
  {
    title: "Add your live URL",
    body: "Verify you own the domain, then LaunchAudit checks the running app the way a visitor would.",
  },
  {
    title: "Press Run",
    body: "Get a Launch Report: a verdict, a 0-10 risk score and every problem with the proof behind it.",
  },
] as const;

const CHECKS = [
  {
    title: "Leaked secrets",
    body: "API keys, tokens and passwords committed to the repo or shipped to the browser.",
  },
  {
    title: "Injection",
    body: "User input that reaches a database query, shell command or template, traced step by step.",
  },
  {
    title: "Login and access control",
    body: "Routes that skip sign-in checks, or let one user read or change another user’s data.",
  },
  {
    title: "Vulnerable dependencies",
    body: "Packages with published security advisories, and the version that fixes them.",
  },
  {
    title: "Live configuration",
    body: "Missing security headers, open CORS, exposed files and debug pages on your live URL.",
  },
  {
    title: "Request forgery and XSS",
    body: "User-controlled URLs and HTML that reach places they should not.",
  },
] as const;

export default function HomePage() {
  return (
    <>
      <section aria-labelledby="hero-title" className="border-b">
        <div className="container-page grid gap-12 py-12 sm:py-16 lg:grid-cols-12 lg:gap-10 lg:py-24">
          <div className="flex flex-col gap-6 lg:col-span-6 lg:pt-6">
            <h1
              id="hero-title"
              className="text-4xl font-bold tracking-[-0.035em] text-balance sm:text-5xl"
            >
              Check your app before you launch it.
            </h1>
            <p className="max-w-prose text-lg text-muted-foreground sm:text-xl">
              Built your app with AI tools? LaunchAudit reads your code and
              probes your live URL, then tells you plainly whether it is safe
              to launch, and shows the proof for every problem it finds.
            </p>
            <div className="flex flex-wrap gap-3 pt-2">
              <ButtonLink href="/audits/new" size="lg">
                Run an audit
              </ButtonLink>
              <ButtonLink href="/reports" size="lg" variant="outline">
                View reports
              </ButtonLink>
            </div>
            <SignInButton />
            <p className="max-w-prose text-sm text-muted-foreground">
              Your code is read, never executed. Live checks only start after
              you verify that you own the domain.
            </p>
          </div>
          <SampleReport className="lg:col-span-6 lg:col-start-7 xl:col-span-5 xl:col-start-8" />
        </div>
      </section>

      <section aria-labelledby="how-title" className="border-b">
        <div className="container-page py-14 sm:py-20">
          <h2 id="how-title" className="text-2xl font-bold tracking-tight sm:text-3xl">
            How an audit works
          </h2>
          <ol className="mt-8 grid gap-8 md:grid-cols-3 md:gap-10">
            {STEPS.map((step, index) => (
              <li key={step.title} className="flex gap-4 md:flex-col md:gap-3">
                <span
                  aria-hidden="true"
                  className="flex size-8 shrink-0 items-center justify-center rounded-md border-2 border-primary font-mono text-sm font-semibold text-primary"
                >
                  {index + 1}
                </span>
                <div className="flex flex-col gap-1.5">
                  <h3 className="text-lg font-semibold">{step.title}</h3>
                  <p className="max-w-prose text-muted-foreground">{step.body}</p>
                </div>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section aria-labelledby="checks-title">
        <div className="container-page grid gap-8 py-14 sm:py-20 lg:grid-cols-12 lg:gap-10">
          <div className="flex flex-col gap-3 lg:col-span-4">
            <h2 id="checks-title" className="text-2xl font-bold tracking-tight sm:text-3xl">
              What it looks for
            </h2>
            <p className="max-w-prose text-muted-foreground">
              The problems that most often slip into apps built quickly, ranked
              Critical, High, Medium or Low so you know what to fix first.
            </p>
          </div>
          <dl className="grid border-t sm:grid-cols-2 sm:gap-x-10 lg:col-span-8">
            {CHECKS.map((check) => (
              <div key={check.title} className="flex flex-col gap-1 border-b py-5">
                <dt className="font-semibold">{check.title}</dt>
                <dd className="text-muted-foreground">{check.body}</dd>
              </div>
            ))}
          </dl>
        </div>
      </section>
    </>
  );
}
