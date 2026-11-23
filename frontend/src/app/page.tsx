import { ButtonLink } from "@/components/button-link";
import { HeroMark } from "@/components/hero-mark";
import { SampleReport } from "@/components/sample-report";

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
    proofKind: "File and line",
    proof: 'src/config.ts:12  OPENAI_API_KEY = "sk-••••"',
  },
  {
    title: "Open database rules",
    body: "Supabase tables without row level security and Firebase rules that let anyone read or write.",
    proofKind: "Rule or policy",
    proof: "notes table: row level security off",
  },
  {
    title: "Login and access control",
    body: "Routes that skip sign-in checks, or let one user read or change another user’s data.",
    proofKind: "Live request as a second user",
    proof: "GET /api/orders/88 as user B → 200 OK",
  },
  {
    title: "Injection",
    body: "User input that reaches a database query, shell command or template, traced step by step.",
    proofKind: "Data-flow trace",
    proof: "req.query.q → sql`…${q}` → db.query()",
  },
  {
    title: "Request forgery and XSS",
    body: "User-controlled URLs and HTML that reach places they should not.",
    proofKind: "Data-flow trace",
    proof: "searchParams.url → fetch(url)",
  },
  {
    title: "Vulnerable dependencies",
    body: "Packages with published security advisories, and the version that fixes them.",
    proofKind: "Package and advisory",
    proof: "lodash 4.17.20, fixed in 4.17.21",
  },
  {
    title: "Live configuration",
    body: "Missing security headers, open CORS, exposed files and debug pages on your live URL.",
    proofKind: "Response headers",
    proof: "x-frame-options: (missing)",
  },
] as const;

export default function HomePage() {
  return (
    <>
      <section aria-labelledby="hero-title" className="border-b">
        <div className="container-page grid gap-12 py-12 sm:py-16 lg:grid-cols-12 lg:gap-10 lg:py-24">
          <div className="flex flex-col gap-10 lg:col-span-6 lg:self-start lg:pt-28">
            <h1
              id="hero-title"
              className="flex items-center gap-3 text-3xl font-bold tracking-[-0.035em] sm:gap-5 sm:text-5xl"
            >
              <HeroMark className="size-12 sm:size-20" />
              <span>LaunchAudit</span>
            </h1>
            <p className="-mt-4 max-w-[24ch] text-xl text-balance text-muted-foreground sm:text-2xl">
              Find out if your app is safe to launch, and see the proof.
            </p>
            <div className="flex flex-wrap gap-3">
              <ButtonLink href="/audits/new" size="lg">
                Run an audit
              </ButtonLink>
              <ButtonLink href="/reports" size="lg" variant="outline">
                View reports
              </ButtonLink>
            </div>
          </div>
          <SampleReport className="lg:col-span-6 lg:col-start-7 xl:col-span-5 xl:col-start-8" />
        </div>
      </section>

      <section aria-labelledby="about-title" className="border-b bg-muted/40">
        <div className="container-page flex flex-col gap-3 py-10 sm:py-12">
          <h2 id="about-title" className="sr-only">
            What LaunchAudit does
          </h2>
          <p className="max-w-prose text-lg text-balance sm:text-xl">
            Built your app with AI tools? LaunchAudit reads your code and
            probes your live URL, then tells you plainly whether it is safe to
            launch, and shows the proof for every problem it finds.
          </p>
          <p className="max-w-prose text-sm text-muted-foreground">
            Your code is read, never executed. Live checks only start after you
            verify that you own the domain.
          </p>
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
          <div className="flex flex-col gap-3 lg:sticky lg:top-24 lg:col-span-4 lg:self-start">
            <h2 id="checks-title" className="text-2xl font-bold tracking-tight sm:text-3xl">
              What it looks for
            </h2>
            <p className="max-w-prose text-muted-foreground">
              The problems that most often slip into apps built quickly, ranked
              Critical, High, Medium or Low so you know what to fix first. Each
              one comes with proof you can check yourself.
            </p>
          </div>
          <ul className="border-t lg:col-span-8">
            {CHECKS.map((check) => (
              <li
                key={check.title}
                className="grid gap-x-8 gap-y-3 border-b py-5 md:grid-cols-[minmax(0,1fr)_minmax(0,18rem)]"
              >
                <div className="flex flex-col gap-1">
                  <h3 className="font-semibold">{check.title}</h3>
                  <p className="text-muted-foreground">{check.body}</p>
                </div>
                <div className="flex min-w-0 flex-col gap-1.5">
                  <p className="text-xs text-muted-foreground">
                    <span className="sr-only">Proof: </span>
                    {check.proofKind}
                  </p>
                  <code className="block rounded-md border bg-card px-2.5 py-1.5 font-mono text-xs leading-5 whitespace-pre-wrap [overflow-wrap:anywhere]">
                    {check.proof}
                  </code>
                </div>
              </li>
            ))}
          </ul>
        </div>
      </section>
    </>
  );
}
