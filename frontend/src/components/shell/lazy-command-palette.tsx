"use client";

import dynamic from "next/dynamic";
import { useState } from "react";

import { useShell } from "./shell-context";

// The palette's code loads the first time it is opened (Ctrl/Cmd+K, "/" or
// the search button), not with every page.
const CommandPalette = dynamic(
  () => import("./command-palette").then((mod) => mod.CommandPalette),
  { ssr: false },
);

export function LazyCommandPalette() {
  const { paletteOpen } = useShell();
  const [opened, setOpened] = useState(false);
  if (paletteOpen && !opened) setOpened(true);
  return opened ? <CommandPalette /> : null;
}
