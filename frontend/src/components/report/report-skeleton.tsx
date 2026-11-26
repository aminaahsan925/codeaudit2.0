import { REPORT_ASIDE, REPORT_GRID, REPORT_PAGE } from "@/components/report/layout";
import { Skeleton } from "@/components/ui/skeleton";

/** Placeholder with the same sizes as the loaded report, so nothing jumps. */
export function ReportSkeleton() {
  return (
    <div role="status" className={REPORT_PAGE}>
      <span className="sr-only">Loading the report.</span>
      <div aria-hidden="true" className="flex flex-col gap-2.5">
        <Skeleton className="h-9 w-64 rounded-lg sm:h-11" />
        <Skeleton className="h-5 w-80 max-w-full" />
      </div>
      <div aria-hidden="true" className={REPORT_GRID}>
        <div className={`${REPORT_ASIDE} overflow-hidden rounded-2xl border bg-card shadow-card`}>
          <div className="h-1 bg-muted" />
          <div className="flex gap-4 bg-sunken px-5 py-5 sm:px-6">
            <Skeleton className="h-[8.25rem] w-12 rounded-full bg-border" />
            <div className="flex flex-1 flex-col gap-2.5 pt-1">
              <Skeleton className="h-4 w-16 bg-border" />
              <Skeleton className="h-10 w-40 bg-border" />
              <Skeleton className="h-4 w-full bg-border" />
              <Skeleton className="h-4 w-3/4 bg-border" />
            </div>
          </div>
          <div className="flex items-center gap-5 border-b px-5 py-5 sm:px-6">
            <Skeleton className="size-32 shrink-0 rounded-full" />
            <div className="flex flex-1 flex-col gap-2">
              <Skeleton className="h-5 w-24" />
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-2/3" />
            </div>
          </div>
          <div className="flex flex-col gap-3 px-5 py-5 sm:px-6">
            <Skeleton className="h-5 w-48" />
            <div className="flex items-center gap-5">
              <Skeleton className="size-24 shrink-0 rounded-full" />
              <div className="grid flex-1 grid-cols-2 gap-2">
                <Skeleton className="h-4" />
                <Skeleton className="h-4" />
                <Skeleton className="h-4" />
                <Skeleton className="h-4" />
              </div>
            </div>
          </div>
        </div>

        <div className="flex min-w-0 flex-col gap-6">
          <Skeleton className="hidden h-[3.75rem] rounded-2xl lg:block" />
          <div className="flex flex-col gap-2">
            <Skeleton className="h-7 w-44" />
            <Skeleton className="h-4 w-72 max-w-full" />
          </div>
          <div className="flex flex-col gap-3">
            {[0, 1, 2].map((row) => (
              <div key={row} className="flex flex-col gap-2.5 rounded-2xl border bg-card p-4 shadow-xs sm:p-5">
                <div className="flex items-center gap-2 sm:gap-4">
                  <Skeleton className="size-7 shrink-0 rounded-lg" />
                  <Skeleton className="h-6 w-24" />
                </div>
                <div className="flex flex-col gap-2.5 sm:pl-11">
                  <Skeleton className="h-6 w-4/5" />
                  <Skeleton className="h-4 w-1/2" />
                  <Skeleton className="h-4 w-2/3" />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
