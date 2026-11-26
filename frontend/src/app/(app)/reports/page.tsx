import type { Metadata } from "next";

import { ReportsHistory } from "./reports-history";

export const metadata: Metadata = {
  title: "Reports",
};

export default function ReportsPage() {
  return <ReportsHistory />;
}
