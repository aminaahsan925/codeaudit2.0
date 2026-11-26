"use client";

import { Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";

import { Button } from "@/components/ui/button";

/*
  The icon and label are switched with the .dark class (set before paint by
  next-themes), so the server render never disagrees with the client.
*/
export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();

  return (
    <Button
      type="button"
      variant="ghost"
      size="icon"
      className="size-9 rounded-[10px] text-muted-foreground hover:bg-sunken hover:text-foreground"
      onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}
    >
      <Moon aria-hidden="true" className="size-[18px] dark:hidden" />
      <Sun aria-hidden="true" className="hidden size-[18px] dark:block" />
      <span className="sr-only dark:hidden">Switch to dark theme</span>
      <span className="sr-only hidden dark:inline">Switch to light theme</span>
    </Button>
  );
}
