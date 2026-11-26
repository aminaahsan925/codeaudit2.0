/*
  Shared layout for the report page, its skeleton and its other states, so
  the loading placeholder lines up with the loaded report.
  --report-sticky-top clears the app shell's top bar for sticky elements.
*/

/** Page wrapper. Extra bottom space on mobile clears the fixed action bar. */
export const REPORT_PAGE =
  "container-page flex flex-col gap-6 pt-6 pb-32 [--report-sticky-top:5rem] sm:gap-8 sm:pt-8 lg:pb-16";

/** Two columns from 1024px: the sticky verdict hero and the findings. */
export const REPORT_GRID =
  "grid items-start gap-6 lg:grid-cols-[minmax(0,22rem)_minmax(0,1fr)] lg:gap-8 xl:grid-cols-[minmax(0,24rem)_minmax(0,1fr)]";

/** The left column: sticky on desktop. */
export const REPORT_ASIDE = "min-w-0 lg:sticky lg:top-(--report-sticky-top)";
