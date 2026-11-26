"use client";

import { Accordion } from "@base-ui/react/accordion";
import { Plus } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";

import { TERMS } from "@/lib/glossary";
import { formatRiskScore } from "@/lib/report";
import { SAMPLE_SCORE } from "@/lib/sample-data";

import { SectionIntro } from "./section-intro";

const QUESTIONS: { q: string; a: ReactNode }[] = [
  {
    q: "Do you run my code?",
    a: "No. LaunchAudit reads your files the way a reviewer would. It never installs your packages, runs your scripts or starts your app.",
  },
  {
    q: "Do I need to be technical?",
    a: "No. Each problem starts with what could happen to your users, in plain words. The technical name and the proof sit underneath, for you or for a developer you work with.",
  },
  {
    q: "What do you need from me?",
    a: "Your code, as a GitHub link or a zip file. That is the only required step. You can also add your live site, and a test login so we can check the pages behind sign-in.",
  },
  {
    q: "Will you test my live site without asking?",
    a: "No. Live checks start only after you prove the site is yours by adding a small verification file. Sites you have not verified are skipped.",
  },
  {
    q: "Is my code stored?",
    a: "A zip upload stays on our server so you can rerun the audit after you fix things. It is never offered for download. Keys and passwords in your report are hidden except for their first few characters.",
  },
  {
    q: "How long does it take?",
    a: "It depends on the size of your app and on whether you add a live site. The progress page shows each step as it runs, and the report opens when the last step finishes.",
  },
  {
    q: "What does the risk score mean?",
    a: (
      <>
        {TERMS.riskScore.plain} The <Link href="#example" className="font-medium text-brand-fg underline underline-offset-4">example report</Link> scores{" "}
        {formatRiskScore(SAMPLE_SCORE)}, so it should not launch yet.
      </>
    ),
  },
  {
    q: "Does a Launch verdict mean my app is secure?",
    a: "No tool can promise that. LaunchAudit checks for the common problems on this page and shows proof for each one it finds. Treat it as a careful first review.",
  },
];

export function Faq() {
  return (
    <section id="faq" aria-labelledby="faq-title" className="scroll-mt-20 py-24 sm:py-28">
      <div className="container-page grid grid-cols-1 gap-10 lg:grid-cols-12 lg:gap-8">
        <SectionIntro id="faq-title" title="Questions founders ask" className="lg:col-span-4">
          Short answers. If yours is missing, the example report is the quickest way to see what you get.
        </SectionIntro>
        <Accordion.Root className="rounded-2xl border bg-card shadow-card lg:col-span-8">
          {QUESTIONS.map(({ q, a }) => (
            <Accordion.Item key={q} className="border-b last:border-b-0">
              <Accordion.Header className="m-0">
                <Accordion.Trigger className="group flex w-full items-center justify-between gap-4 rounded-2xl px-5 py-5 text-left font-display text-lg font-medium tracking-[-0.015em] transition-colors hover:text-brand-fg focus-visible:-outline-offset-2 sm:px-6">
                  {q}
                  <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-sunken text-muted-foreground transition-transform duration-200 group-data-panel-open:rotate-45 group-data-panel-open:bg-brand-soft group-data-panel-open:text-brand-fg">
                    <Plus aria-hidden="true" className="size-4" />
                  </span>
                </Accordion.Trigger>
              </Accordion.Header>
              <Accordion.Panel
                hiddenUntilFound
                className="transition-opacity duration-200 data-ending-style:opacity-0 data-starting-style:opacity-0"
              >
                <p className="max-w-2xl px-5 pb-6 text-muted-foreground sm:px-6">{a}</p>
              </Accordion.Panel>
            </Accordion.Item>
          ))}
        </Accordion.Root>
      </div>
    </section>
  );
}
