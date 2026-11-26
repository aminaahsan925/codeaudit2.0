import { ButtonLink } from "@/components/button-link";

/*
  An ink panel in both themes. Light: the ink colour on the paper canvas.
  Dark: a raised panel on the dark canvas. The button is the inverse of the
  panel, so its text stays at ink contrast (about 15:1) either way.
*/
export function FinalCta() {
  return (
    <section aria-labelledby="cta-title" className="pb-24 sm:pb-28">
      <div className="container-page">
        <div className="rounded-[20px] bg-foreground px-6 py-14 text-background shadow-card ring-1 ring-brand/25 ring-inset sm:px-12 sm:py-16 lg:px-16 dark:border dark:bg-card dark:text-foreground">
          <div className="grid grid-cols-1 gap-8 lg:grid-cols-12 lg:items-center">
            <div className="flex flex-col gap-4 lg:col-span-8">
              <h2 id="cta-title" className="text-3xl leading-[1.12] font-medium sm:text-[2.5rem]">
                Find the problems before your users do.
              </h2>
              <p className="max-w-xl text-lg text-background/80 dark:text-muted-foreground">
                Add your code and get a verdict, with proof for every problem.
              </p>
            </div>
            <div className="lg:col-span-4 lg:justify-self-end">
              <ButtonLink
                href="/audits/new"
                size="lg"
                className="bg-background text-foreground hover:bg-background/90 focus-visible:ring-2 focus-visible:ring-background focus-visible:ring-offset-2 focus-visible:ring-offset-foreground dark:bg-foreground dark:text-background dark:hover:bg-foreground/90 dark:focus-visible:ring-foreground dark:focus-visible:ring-offset-card"
              >
                Run an audit
              </ButtonLink>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
