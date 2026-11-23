import { Skeleton } from "@/components/ui/skeleton";

export default function Loading() {
  return (
    <div
      role="status"
      aria-live="polite"
      className="container-page flex flex-col gap-8 py-10 sm:py-14"
    >
      <span className="sr-only">Loading page</span>
      <div className="flex max-w-prose flex-col gap-3" aria-hidden="true">
        <Skeleton className="h-10 w-2/3" />
        <Skeleton className="h-5 w-full" />
        <Skeleton className="h-5 w-4/5" />
      </div>
      <Skeleton aria-hidden="true" className="h-56 w-full rounded-lg" />
    </div>
  );
}
