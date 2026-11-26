import { domAnimation } from "motion/react";

// Loaded after hydration by LazyMotion in providers.tsx, so the animation
// features stay out of every route's first-load JavaScript.
export default domAnimation;
