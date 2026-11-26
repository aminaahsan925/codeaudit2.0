"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { LazyMotion, MotionConfig } from "motion/react";
import { ThemeProvider } from "next-themes";
import { useState, type ReactNode } from "react";

import { TooltipProvider } from "@/components/ui/tooltip";
import { isApiError } from "@/lib/api";

// Animation features load right after hydration, outside the first-load
// bundle. `m` elements hold their initial style until they arrive.
const loadMotionFeatures = () =>
  import("@/components/ui/motion-features").then((mod) => mod.default);

function makeQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        refetchOnWindowFocus: true,
        retry: (failureCount, error) => {
          // Client errors (4xx) will not fix themselves on retry.
          if (isApiError(error) && error.status !== null && error.status < 500) {
            return false;
          }
          return failureCount < 2;
        },
      },
    },
  });
}

export function Providers({ children }: { children: ReactNode }) {
  const [queryClient] = useState(makeQueryClient);

  return (
    <ThemeProvider
      attribute="class"
      defaultTheme="light"
      enableSystem
      disableTransitionOnChange
    >
      <QueryClientProvider client={queryClient}>
        {/* LazyMotion keeps the animation runtime small; MotionConfig turns
            every animation off when the OS asks for reduced motion. */}
        <LazyMotion features={loadMotionFeatures} strict>
          <MotionConfig reducedMotion="user">
            <TooltipProvider delay={200}>{children}</TooltipProvider>
          </MotionConfig>
        </LazyMotion>
      </QueryClientProvider>
    </ThemeProvider>
  );
}
