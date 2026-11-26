import { Skeleton } from "@/components/ui/skeleton";

// Sizes match the page header (text-3xl title, text-lg intro) and the
// first rows of content, so nothing shifts when the page arrives.
export default function Loading() {
  return (
    <div
      role="status"
      aria-live="polite"
      className="container-page flex flex-col gap-8 py-10 sm:py-14"
    >
      <span className="sr-only">Loading page</span>
      <div className="flex max-w-prose flex-col gap-3" aria-hidden="true">
        <Skeleton className="h-[2.375rem] w-64 rounded-[10px]" />
        <Skeleton className="h-7 w-full max-w-[28rem] rounded-[8px]" />
      </div>
      <div className="flex flex-col gap-3" aria-hidden="true">
        {[0, 1, 2].map((row) => (
          <div
            key={row}
            className="flex h-[5.5rem] items-center gap-4 rounded-2xl border border-border bg-card px-5 shadow-xs"
          >
            <div className="flex min-w-0 flex-1 flex-col gap-2">
              <Skeleton className="h-5 w-48 max-w-full" />
              <Skeleton className="h-4 w-32" />
            </div>
            <Skeleton className="h-6 w-20 rounded-[6px]" />
          </div>
        ))}
      </div>
    </div>
  );
}
