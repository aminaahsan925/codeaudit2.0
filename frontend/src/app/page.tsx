import { ButtonLink } from "@/components/button-link";
import {
  GlobeIcon,
  InjectionIcon,
  KeyIcon,
  LockIcon,
  PackageIcon,
  ShieldScriptIcon,
} from "@/components/graphics/check-icons";
import { HeroIllustration } from "@/components/graphics/hero-illustration";
import {
  CodeInIcon,
  ReportIcon,
  ScanIcon,
} from "@/components/graphics/step-icons";
import { SampleReport } from "@/components/sample-report";
import { SignInButton } from "@/components/sign-in-button";

const STEPS = [
  {
    icon: CodeInIcon,
    title: "Add your code",
    body: "GitHub repo or zip.",
  },
  {
    icon: ScanIcon,
    title: "Add your live URL",
    body: "Verify your domain.",
  },
  {
    icon: ReportIcon,
    title: "Press Run",
    body: "Verdict, risk score, proof.",
  },
] as const;

const CHECKS = [
  {
    icon: KeyIcon,
    title: "Leaked secrets",
    body: "Keys and passwords in code or the browser.",
  },
  {
    icon: InjectionIcon,
    title: "Injection",
    body: "Input reaching a query, shell or template.",
  },
  {
    icon: LockIcon,
    title: "Login and access control",
    body: "Missing sign-in checks, cross-user access.",
  },
  {
    icon: PackageIcon,
    title: "Vulnerable dependencies",
    body: "Packages with known advisories.",
  },
  {
    icon: GlobeIcon,
    title: "Live configuration",
    body: "Headers, CORS, exposed files, debug pages.",
  },
  {
    icon: ShieldScriptIcon,
    title: "Request forgery and XSS",
    body: "Bad URLs and HTML in the wrong place.",
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
              Built your app with AI tools? Get a plain verdict on whether it
              is safe to launch, with proof for every problem.
            </p>
            <HeroIllustration className="max-w-md" />
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
              Your code is read, never run.
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
          <ol className="relative mt-8 grid gap-8 md:grid-cols-3 md:gap-10">
            {/* Dashed flow line behind the step icons on wide screens. */}
            <div
              aria-hidden="true"
              className="absolute inset-x-0 top-6 hidden border-t-2 border-dashed border-input md:block"
            />
            {STEPS.map((step) => (
              <li key={step.title} className="relative flex flex-col gap-3">
                <span className="flex size-12 items-center justify-center rounded-full border bg-background text-primary">
                  <step.icon className="size-6" />
                </span>
                <div className="flex flex-col gap-1">
                  <h3 className="text-lg font-semibold">{step.title}</h3>
                  <p className="max-w-prose text-muted-foreground">{step.body}</p>
                </div>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section aria-labelledby="checks-title">
        <div className="container-page py-14 sm:py-20">
          <div className="flex flex-col gap-3">
            <h2 id="checks-title" className="text-2xl font-bold tracking-tight sm:text-3xl">
              What it looks for
            </h2>
            <p className="max-w-prose text-muted-foreground">
              Ranked Critical to Low, so you fix the worst first.
            </p>
          </div>
          <ul className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {CHECKS.map((check) => (
              <li
                key={check.title}
                className="flex flex-col gap-3 rounded-lg border bg-card p-5"
              >
                <check.icon className="size-7 text-primary" />
                <div className="flex flex-col gap-1">
                  <h3 className="font-semibold">{check.title}</h3>
                  <p className="text-sm text-muted-foreground">{check.body}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>
      </section>
    </>
  );
}
