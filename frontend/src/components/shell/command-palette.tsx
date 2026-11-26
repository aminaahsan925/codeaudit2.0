"use client";

import { Dialog } from "@base-ui/react/dialog";
import {
  ArrowDown,
  ArrowUp,
  CircleHelp,
  CornerDownLeft,
  FilePlus2,
  FileText,
  ListChecks,
  Search,
  SearchX,
  SunMoon,
  type LucideIcon,
} from "lucide-react";
import * as m from "motion/react-m";
import { useRouter } from "next/navigation";
import { useTheme } from "next-themes";
import { useCallback, useEffect, useId, useMemo, useRef, useState, type KeyboardEvent, type RefObject } from "react";

import { popIn } from "@/components/ui/motion";
import { useRunsHistory } from "@/hooks/use-runs-history";
import { formatDateTime } from "@/lib/dates";
import { RUN_STATUS_LABEL } from "@/lib/report";
import { cn } from "@/lib/utils";

import { Kbd } from "./kbd";
import { useShell } from "./shell-context";

const MAX_RECENT = 5;

interface Command {
  id: string;
  group: "actions" | "recent";
  label: string;
  hint?: string;
  keywords?: string;
  icon: LucideIcon;
  run: () => void;
}

const GROUP_LABEL: Record<Command["group"], string> = {
  actions: "Actions",
  recent: "Recent reports",
};

function matches(command: Command, query: string): boolean {
  const q = query.trim().toLowerCase();
  if (!q) return true;
  return `${command.label} ${command.keywords ?? ""}`.toLowerCase().includes(q);
}

/** Mounted only while the palette is open, so history fetches start on open. */
function PaletteBody({
  onDone,
  inputRef,
}: {
  onDone: () => void;
  inputRef: RefObject<HTMLInputElement | null>;
}) {
  const router = useRouter();
  const { resolvedTheme, setTheme } = useTheme();
  const { entries } = useRunsHistory();
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const baseId = useId();
  const listId = `${baseId}-list`;
  const optionId = (command: Command) => `${baseId}-option-${command.id}`;

  const commands = useMemo<Command[]>(() => {
    const go = (href: string) => () => {
      onDone();
      router.push(href);
    };
    const nextTheme = resolvedTheme === "dark" ? "light" : "dark";
    const actions: Command[] = [
      { id: "new-audit", group: "actions", label: "New audit", keywords: "run start scan", icon: FilePlus2, run: go("/audits/new") },
      { id: "reports", group: "actions", label: "View reports", keywords: "history list", icon: ListChecks, run: go("/reports") },
      {
        id: "theme",
        group: "actions",
        label: "Switch theme",
        hint: nextTheme === "dark" ? "Use dark" : "Use light",
        keywords: "dark light mode appearance",
        icon: SunMoon,
        run: () => {
          onDone();
          setTheme(nextTheme);
        },
      },
      { id: "help", group: "actions", label: "Help", keywords: "faq questions support", icon: CircleHelp, run: go("/#faq") },
    ];
    const recent: Command[] = (entries ?? []).slice(0, MAX_RECENT).map(({ stored, run }) => {
      const status = run ? RUN_STATUS_LABEL[run.status] : null;
      const date = formatDateTime(stored.createdAt);
      return {
        id: `run-${stored.id}`,
        group: "recent",
        label: stored.projectName,
        hint: [status, date].filter(Boolean).join(", ") || undefined,
        icon: FileText,
        run: go(run?.status === "succeeded" ? `/reports/${stored.id}` : `/audits/${stored.id}`),
      };
    });
    return [...actions, ...recent];
  }, [entries, onDone, resolvedTheme, router, setTheme]);

  const visible = commands.filter((command) => matches(command, query));
  const activeIndex = visible.length === 0 ? -1 : Math.min(active, visible.length - 1);
  const activeCommand = activeIndex >= 0 ? visible[activeIndex] : undefined;
  const activeId = activeCommand ? optionId(activeCommand) : undefined;
  const groups = (["actions", "recent"] as const)
    .map((group) => ({ group, items: visible.filter((command) => command.group === group) }))
    .filter(({ items }) => items.length > 0);

  useEffect(() => {
    if (!activeId) return;
    document.getElementById(activeId)?.scrollIntoView?.({ block: "nearest" });
  }, [activeId]);

  function onKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (visible.length === 0) return;
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActive((activeIndex + 1) % visible.length);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActive((activeIndex - 1 + visible.length) % visible.length);
    } else if (event.key === "Enter" && activeCommand) {
      event.preventDefault();
      activeCommand.run();
    }
  }

  return (
    <>
      <div className="flex h-14 items-center gap-3 border-b border-border px-4">
        <Search aria-hidden="true" className="size-[18px] shrink-0 text-muted-foreground" />
        <input
          ref={inputRef}
          type="text"
          role="combobox"
          aria-label="Search actions and reports"
          aria-expanded={visible.length > 0}
          aria-controls={listId}
          aria-autocomplete="list"
          aria-activedescendant={activeId}
          autoComplete="off"
          spellCheck={false}
          placeholder="Search actions and reports"
          value={query}
          onChange={(event) => {
            setQuery(event.target.value);
            setActive(0);
          }}
          onKeyDown={onKeyDown}
          className="h-full min-w-0 flex-1 bg-transparent text-base text-foreground outline-none placeholder:text-muted-foreground"
        />
        <Dialog.Close
          aria-label="Close"
          className="inline-flex shrink-0 items-center rounded-[6px] outline-offset-2"
        >
          <Kbd>Esc</Kbd>
        </Dialog.Close>
      </div>

      <span role="status" className="sr-only">
        {visible.length === 1 ? "1 result" : `${visible.length} results`}
      </span>

      {visible.length === 0 ? (
        <div className="flex flex-col items-center gap-2 px-6 py-12 text-center">
          <span className="mb-1 inline-flex size-10 items-center justify-center rounded-xl border border-border bg-sunken text-muted-foreground">
            <SearchX aria-hidden="true" className="size-5" />
          </span>
          <p className="text-sm font-medium text-foreground">
            Nothing matches &quot;{query.trim()}&quot;
          </p>
          <p className="max-w-72 text-sm text-muted-foreground">
            Check the spelling, or search for a project name.
          </p>
        </div>
      ) : (
        <div
          id={listId}
          role="listbox"
          aria-label="Results"
          className="max-h-[min(24rem,60vh)] overflow-y-auto overscroll-contain p-2"
        >
          {groups.map(({ group, items }) => {
            const labelId = `${baseId}-${group}`;
            return (
              <div key={group} role="group" aria-labelledby={labelId} className="pb-1">
                <div
                  id={labelId}
                  role="presentation"
                  className="px-3 pt-2 pb-1.5 text-xs font-medium text-muted-foreground"
                >
                  {GROUP_LABEL[group]}
                </div>
                {items.map((command) => {
                  const selected = command.id === activeCommand?.id;
                  const Icon = command.icon;
                  return (
                    <div
                      key={command.id}
                      id={optionId(command)}
                      role="option"
                      tabIndex={-1}
                      aria-selected={selected}
                      onMouseMove={() => {
                        if (!selected) setActive(visible.indexOf(command));
                      }}
                      onClick={() => command.run()}
                      className={cn(
                        "flex h-11 cursor-pointer items-center gap-3 rounded-[10px] px-3 text-sm",
                        selected ? "bg-accent text-foreground" : "text-foreground",
                      )}
                    >
                      <span
                        aria-hidden="true"
                        className={cn(
                          "inline-flex size-7 shrink-0 items-center justify-center rounded-[8px] border",
                          selected
                            ? "border-transparent bg-brand-soft text-brand-fg"
                            : "border-border bg-sunken text-muted-foreground",
                        )}
                      >
                        <Icon className="size-4" strokeWidth={1.9} />
                      </span>
                      <span className="min-w-0 truncate font-medium">{command.label}</span>
                      {command.hint ? (
                        <span className="ml-auto shrink-0 truncate pl-3 text-xs text-muted-foreground">
                          {command.hint}
                        </span>
                      ) : null}
                      <CornerDownLeft
                        aria-hidden="true"
                        className={cn(
                          "size-4 shrink-0 text-muted-foreground",
                          command.hint ? "" : "ml-auto",
                          selected ? "opacity-100" : "opacity-0",
                        )}
                      />
                    </div>
                  );
                })}
              </div>
            );
          })}
        </div>
      )}

      <div
        aria-hidden="true"
        className="hidden items-center gap-4 border-t border-border bg-sunken/60 px-4 py-2.5 text-xs text-muted-foreground sm:flex"
      >
        <span className="inline-flex items-center gap-1.5">
          <Kbd className="px-1">
            <ArrowUp className="size-3" />
          </Kbd>
          <Kbd className="px-1">
            <ArrowDown className="size-3" />
          </Kbd>
          to move
        </span>
        <span className="inline-flex items-center gap-1.5">
          <Kbd>Enter</Kbd> to open
        </span>
        <span className="inline-flex items-center gap-1.5">
          <Kbd>Esc</Kbd> to close
        </span>
      </div>
    </>
  );
}

/** Ctrl/Cmd+K or "/" opens it; Esc closes it. */
export function CommandPalette() {
  const { paletteOpen, setPaletteOpen } = useShell();
  const inputRef = useRef<HTMLInputElement | null>(null);
  const close = useCallback(() => setPaletteOpen(false), [setPaletteOpen]);

  return (
    <Dialog.Root open={paletteOpen} onOpenChange={setPaletteOpen}>
      <Dialog.Portal>
        <Dialog.Backdrop className="glass fixed inset-0 z-50 transition-opacity duration-150 data-ending-style:opacity-0 data-starting-style:opacity-0" />
        <Dialog.Popup
          initialFocus={inputRef}
          className="fixed inset-x-4 top-[12vh] z-50 mx-auto max-w-[40rem] outline-none transition-opacity duration-150 data-ending-style:opacity-0"
        >
          <m.div
            variants={popIn}
            initial="hidden"
            animate="show"
            className="overflow-hidden rounded-[20px] border border-border bg-popover text-popover-foreground shadow-float"
          >
            <Dialog.Title className="sr-only">Search</Dialog.Title>
            <Dialog.Description className="sr-only">
              Type to filter actions and recent reports. Use the arrow keys to move and Enter to open.
            </Dialog.Description>
            <PaletteBody onDone={close} inputRef={inputRef} />
          </m.div>
        </Dialog.Popup>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
