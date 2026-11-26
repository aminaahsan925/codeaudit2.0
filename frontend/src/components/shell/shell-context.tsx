"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  useSyncExternalStore,
  type ReactNode,
} from "react";

export const SIDEBAR_STORAGE_KEY = "launchaudit:sidebar-collapsed:v1";
const SIDEBAR_CHANGED_EVENT = "launchaudit:sidebar-changed";

function readCollapsed(): boolean {
  try {
    return window.localStorage.getItem(SIDEBAR_STORAGE_KEY) === "1";
  } catch {
    return false;
  }
}

function subscribeCollapsed(onChange: () => void): () => void {
  const onStorage = (event: StorageEvent) => {
    if (event.key === null || event.key === SIDEBAR_STORAGE_KEY) onChange();
  };
  window.addEventListener("storage", onStorage);
  window.addEventListener(SIDEBAR_CHANGED_EVENT, onChange);
  return () => {
    window.removeEventListener("storage", onStorage);
    window.removeEventListener(SIDEBAR_CHANGED_EVENT, onChange);
  };
}

function writeCollapsed(collapsed: boolean): void {
  try {
    window.localStorage.setItem(SIDEBAR_STORAGE_KEY, collapsed ? "1" : "0");
  } catch {
    // Storage unavailable: the choice lasts for this page only.
  }
  window.dispatchEvent(new Event(SIDEBAR_CHANGED_EVENT));
}

function isEditableTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  if (target.isContentEditable) return true;
  const tag = target.tagName;
  return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT";
}

interface ShellState {
  /** Sidebar shown as an icon rail. Always false on the server render. */
  collapsed: boolean;
  /** True only after the user toggled the sidebar, so labels animate on that action alone. */
  collapseChanged: boolean;
  toggleCollapsed: () => void;
  paletteOpen: boolean;
  setPaletteOpen: (open: boolean) => void;
  drawerOpen: boolean;
  setDrawerOpen: (open: boolean) => void;
}

const ShellContext = createContext<ShellState | null>(null);

export function useShell(): ShellState {
  const value = useContext(ShellContext);
  if (!value) throw new Error("useShell must be used inside <ShellProvider>");
  return value;
}

export function ShellProvider({ children }: { children: ReactNode }) {
  // Server snapshot is "expanded", so the first client render matches it;
  // the stored choice applies right after hydration.
  const collapsed = useSyncExternalStore(subscribeCollapsed, readCollapsed, () => false);
  const [collapseChanged, setCollapseChanged] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);

  const toggleCollapsed = useCallback(() => {
    setCollapseChanged(true);
    writeCollapsed(!readCollapsed());
  }, []);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.defaultPrevented || event.isComposing) return;
      const mod = event.metaKey || event.ctrlKey;
      if (mod && !event.altKey && !event.shiftKey && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setPaletteOpen((open) => !open);
        return;
      }
      if (event.key === "/" && !mod && !event.altKey && !isEditableTarget(event.target)) {
        event.preventDefault();
        setPaletteOpen(true);
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  const value = useMemo<ShellState>(
    () => ({
      collapsed,
      collapseChanged,
      toggleCollapsed,
      paletteOpen,
      setPaletteOpen,
      drawerOpen,
      setDrawerOpen,
    }),
    [collapsed, collapseChanged, toggleCollapsed, paletteOpen, drawerOpen],
  );

  return <ShellContext.Provider value={value}>{children}</ShellContext.Provider>;
}

const noopSubscribe = () => () => {};

/** "⌘" on Apple platforms, "Ctrl" elsewhere. The server render says "Ctrl". */
export function useModifierLabel(): "⌘" | "Ctrl" {
  return useSyncExternalStore(
    noopSubscribe,
    () => (/Mac|iPhone|iPad|iPod/.test(navigator.userAgent) ? "⌘" : "Ctrl"),
    () => "Ctrl",
  );
}
