import type { Transition, Variants } from "motion/react";

/*
  The one motion vocabulary for LaunchAudit (docs/design.md, Motion).
  150 to 400 ms, transform and opacity only. MotionConfig reducedMotion="user"
  in providers.tsx renders every one of these in its final state when the OS
  asks for reduced motion.
*/

export const EASE_OUT = [0.22, 0.8, 0.2, 1] as const;

export const SPRING: Transition = { type: "spring", stiffness: 420, damping: 34 };
export const SOFT_SPRING: Transition = { type: "spring", stiffness: 260, damping: 30 };

/** Content entering the page: a short rise and fade. */
export const fadeRise: Variants = {
  hidden: { opacity: 0, y: 10 },
  show: { opacity: 1, y: 0, transition: { duration: 0.32, ease: EASE_OUT } },
};

/** Parent for lists whose rows enter one after another. */
export const stagger = (step = 0.05, delay = 0.08): Variants => ({
  hidden: {},
  show: { transition: { staggerChildren: step, delayChildren: delay } },
});

/** A list row inside a `stagger` parent. */
export const rowIn: Variants = {
  hidden: { opacity: 0, y: 8 },
  show: { opacity: 1, y: 0, transition: { duration: 0.24, ease: EASE_OUT } },
};

/** Something that lands with weight: the verdict, a finding popping in. */
export const popIn: Variants = {
  hidden: { opacity: 0, scale: 0.94, y: 6 },
  show: { opacity: 1, scale: 1, y: 0, transition: SPRING },
};

/** Scroll-triggered reveal props for marketing sections. */
export const revealOnScroll = {
  initial: "hidden",
  whileInView: "show",
  viewport: { once: true, margin: "0px 0px -12% 0px" },
  variants: fadeRise,
} as const;

/** Hover lift for interactive cards. */
export const hoverLift = {
  whileHover: { y: -3, transition: { duration: 0.18, ease: EASE_OUT } },
  whileTap: { scale: 0.99 },
} as const;

/** Press feedback for buttons. */
export const press = { whileTap: { scale: 0.97 } } as const;
