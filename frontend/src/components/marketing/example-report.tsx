import { ButtonLink } from "@/components/button-link";
import { Reveal } from "@/components/ui/reveal";
import { SAMPLE_PROJECT } from "@/lib/sample-data";

import { ReportPreview } from "./report-preview";
import { SectionIntro } from "./section-intro";

export function ExampleReport() {
  return (
    <section id="example" aria-labelledby="example-title" className="scroll-mt-20 bg-sunken py-24 sm:py-28">
      <div className="container-page">
        <SectionIntro id="example-title" title="Click through an example report">
          This is a report for {SAMPLE_PROJECT.name}, a fictional app. Select a
          problem to see the proof behind it.
        </SectionIntro>
        <Reveal className="mt-12">
          <ReportPreview />
        </Reveal>
        <div className="mt-10 flex flex-col items-start gap-4 sm:flex-row sm:items-center">
          <ButtonLink href="/audits/new" size="lg">
            Run your own audit
          </ButtonLink>
          <p className="text-sm text-muted-foreground">
            Your report uses your own code and shows the same kind of proof.
          </p>
        </div>
      </div>
    </section>
  );
}
