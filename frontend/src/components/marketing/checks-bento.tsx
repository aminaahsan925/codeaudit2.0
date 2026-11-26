import { Database, Globe, KeyRound, Package, TextCursorInput, UsersRound, type LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

import { SeverityBadge } from "@/components/severity-badge";
import { RevealGroup, RevealItem } from "@/components/ui/reveal";
import { CATEGORY_PLAIN } from "@/lib/glossary";
import { SAMPLE_FILE, SAMPLE_FINDINGS } from "@/lib/sample-data";
import { cn } from "@/lib/utils";

import { SectionIntro } from "./section-intro";

function sampleFinding(id: string) {
  const finding = SAMPLE_FINDINGS.find((f) => f.id === id);
  if (!finding) throw new Error(`Missing sample finding: ${id}`);
  return finding;
}

const secret = sampleFinding("secret");
const access = sampleFinding("access");
const cors = sampleFinding("cors");

/*
  Every tile rests at shadow-card. On hover it rises 4px, and a float shadow
  on a pseudo-element fades in: only transform and opacity animate.
*/
const TILE =
  "relative isolate w-full rounded-2xl border bg-card p-6 shadow-card transition-transform duration-200 ease-out hover:-translate-y-1 " +
  "after:pointer-events-none after:absolute after:inset-0 after:-z-10 after:rounded-2xl after:opacity-0 after:shadow-float after:transition-opacity after:duration-200 hover:after:opacity-100 motion-reduce:hover:translate-y-0";

function TileHeading({ icon: Icon, title, term, large }: { icon: LucideIcon; title: string; term: string; large?: boolean }) {
  return (
    <>
      <span className="flex size-10 items-center justify-center rounded-xl bg-brand-soft text-brand-fg">
        <Icon aria-hidden="true" className="size-5" />
      </span>
      <div className="flex flex-col gap-1.5">
        <h3 className={cn("leading-tight", large ? "text-2xl" : "text-xl")}>{title}</h3>
        <p className="text-sm text-foreground/80">{term}</p>
      </div>
    </>
  );
}

function Tile({
  icon,
  title,
  term,
  why,
  children,
  className,
}: {
  icon: LucideIcon;
  title: string;
  term: string;
  why: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <RevealItem className={cn("flex min-w-0", className)}>
      <article className={cn(TILE, "flex flex-col gap-5")}>
        <TileHeading icon={icon} title={title} term={term} />
        <p>{why}</p>
        <div className="mt-auto">{children}</div>
      </article>
    </RevealItem>
  );
}

/** The lead tile: the text on the left, the code excerpt on the right. */
function WideTile({
  icon,
  title,
  term,
  why,
  children,
  className,
}: {
  icon: LucideIcon;
  title: string;
  term: string;
  why: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <RevealItem className={cn("flex min-w-0", className)}>
      <article className={cn(TILE, "grid grid-cols-1 gap-6 lg:grid-cols-12 lg:items-center lg:gap-10 lg:p-8")}>
        <div className="flex flex-col gap-5 lg:col-span-5">
          <TileHeading icon={icon} title={title} term={term} large />
          <p className="text-lg">{why}</p>
        </div>
        <div className="min-w-0 lg:col-span-7">{children}</div>
      </article>
    </RevealItem>
  );
}

function Proof({ children }: { children: ReactNode }) {
  return (
    <code className="block overflow-hidden rounded-lg bg-sunken px-3 py-2.5 font-mono text-xs leading-5 text-ellipsis whitespace-pre text-foreground">
      {children}
    </code>
  );
}

/** Three lines of the sample file around the leaked key, the key line flagged. */
function SecretExcerpt() {
  const line = secret.line ?? 1;
  const from = Math.max(1, line - 2);
  const lines = SAMPLE_FILE.lines.slice(from - 1, line + 2);
  return (
    <div className="overflow-hidden rounded-xl border bg-sunken">
      <div className="flex flex-col gap-2 border-b bg-card px-4 py-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <SeverityBadge severity={secret.severity} />
          <span className="font-mono text-xs text-muted-foreground">{secret.where}</span>
        </div>
        <p className="text-sm font-medium">{secret.plainTitle}</p>
      </div>
      <ol className="py-2 font-mono text-xs leading-6">
        {lines.map((text, i) => {
          const n = from + i;
          const flagged = n === line;
          return (
            <li
              key={n}
              className={cn(
                "flex border-l-2 pr-3",
                flagged ? "border-sev-critical bg-sev-critical-tint" : "border-transparent",
              )}
            >
              <span aria-hidden="true" className="w-9 shrink-0 pr-3 text-right text-muted-foreground tabular-nums">
                {n}
              </span>
              <span className="min-w-0 truncate whitespace-pre">{text || " "}</span>
            </li>
          );
        })}
      </ol>
      <p className="border-t bg-card px-4 py-3 text-sm text-muted-foreground">
        <span className="font-medium text-foreground">Suggested fix.</span> Move the key to
        your server and replace it with a new one.
      </p>
    </div>
  );
}

export function ChecksBento() {
  return (
    <section id="checks" aria-labelledby="checks-title" className="scroll-mt-20 bg-sunken pt-36 pb-24 sm:pb-28">
      <div className="container-page">
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-12 lg:items-end">
          <SectionIntro id="checks-title" title="What LaunchAudit looks for" className="lg:col-span-7" />
          <p className="text-lg text-foreground/80 lg:col-span-5">
            The mistakes we see most in apps built fast. Every problem in your
            report comes with the code line or web response that proves it.
          </p>
        </div>

        <RevealGroup className="mt-12 grid grid-cols-1 gap-5 md:grid-cols-2 lg:grid-cols-12">
          <WideTile
            icon={KeyRound}
            title="Keys and passwords left in your code"
            term="Exposed secrets"
            why={CATEGORY_PLAIN.secrets.plain}
            className="md:col-span-2 lg:col-span-12"
          >
            <SecretExcerpt />
          </WideTile>
          <Tile
            icon={Database}
            title="Database rules that let anyone in"
            term="Supabase row level security, Firebase rules"
            why="Without rules, any visitor can read or change every row."
            className="lg:col-span-6"
          >
            <Proof>{'policy "notes" for select using (true)'}</Proof>
          </Tile>
          <Tile
            icon={UsersRound}
            title="Users who can see each other’s data"
            term="Broken access control"
            why={CATEGORY_PLAIN.access_control.plain}
            className="lg:col-span-6"
          >
            <Proof>{access.proof}</Proof>
          </Tile>
          <Tile
            icon={TextCursorInput}
            title="Text boxes that reach your database"
            term="Injection"
            why={CATEGORY_PLAIN.injection.plain}
            className="lg:col-span-4"
          >
            <Proof>{`where email = '" + input + "'`}</Proof>
          </Tile>
          <Tile
            icon={Package}
            title="Packages with known security bugs"
            term="Vulnerable dependencies"
            why={CATEGORY_PLAIN.dependency.plain}
            className="lg:col-span-4"
          >
            <Proof>jsonwebtoken: update to the fixed version</Proof>
          </Tile>
          <Tile
            icon={Globe}
            title="Missing safety settings on your live site"
            term="Security headers and CORS"
            why={CATEGORY_PLAIN.config.plain}
            className="md:col-span-2 lg:col-span-4"
          >
            <Proof>{cors.proof}</Proof>
          </Tile>
        </RevealGroup>
      </div>
    </section>
  );
}
