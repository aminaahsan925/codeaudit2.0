import { ButtonLink } from "@/components/button-link";

import { HeroVisual } from "./hero-visual";

export function Hero() {
  return (
    <section aria-labelledby="hero-title" className="relative isolate overflow-x-clip">
      <div aria-hidden="true" className="absolute inset-0 -z-10 bg-grid-texture" />
      <div className="container-page grid grid-cols-1 items-center gap-14 pt-12 pb-24 sm:pt-16 lg:grid-cols-12 lg:gap-8 lg:pt-14 lg:pb-20">
        <div className="flex min-w-0 flex-col items-start gap-6 lg:col-span-6">
          <h1
            id="hero-title"
            className="font-display text-[2.5rem] leading-[1.06] font-medium tracking-[-0.035em] sm:text-5xl sm:leading-[1.04] xl:text-[3.5rem]"
          >
            Find out if your app is safe to launch.
          </h1>
          <p className="max-w-[34rem] text-lg text-muted-foreground sm:text-xl sm:leading-8">
            You built it with AI tools. LaunchAudit reads your code and your
            live site, then tells you in plain words what to fix first.
          </p>
          <div className="flex flex-wrap gap-3 pt-1">
            <ButtonLink href="/audits/new" size="lg">
              Run an audit
            </ButtonLink>
            <ButtonLink href="#example" variant="outline" size="lg" className="bg-card">
              See an example
            </ButtonLink>
          </div>
          <p className="text-sm text-muted-foreground">
            Your code is read, never run. No security knowledge needed.
          </p>
        </div>
        <HeroVisual className="min-w-0 lg:col-span-6 lg:pl-2 xl:pl-6" />
      </div>
    </section>
  );
}
