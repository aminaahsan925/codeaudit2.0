"use client";

import * as m from "motion/react-m";
import type { ReactNode } from "react";

import { rowIn, stagger, revealOnScroll } from "./motion";

/** Fades and lifts its children in once they scroll into view. */
export function Reveal({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <m.div {...revealOnScroll} className={className}>
      {children}
    </m.div>
  );
}

/** A grid or list whose children (RevealItem) enter one after another on scroll. */
export function RevealGroup({
  children,
  className,
  as = "div",
}: {
  children: ReactNode;
  className?: string;
  as?: "div" | "ul" | "ol";
}) {
  const Comp = as === "ul" ? m.ul : as === "ol" ? m.ol : m.div;
  return (
    <Comp
      initial="hidden"
      whileInView="show"
      viewport={{ once: true, margin: "0px 0px -10% 0px" }}
      variants={stagger(0.06, 0.05)}
      className={className}
    >
      {children}
    </Comp>
  );
}

export function RevealItem({
  children,
  className,
  as = "div",
}: {
  children: ReactNode;
  className?: string;
  as?: "div" | "li";
}) {
  const Comp = as === "li" ? m.li : m.div;
  return (
    <Comp variants={rowIn} className={className}>
      {children}
    </Comp>
  );
}
