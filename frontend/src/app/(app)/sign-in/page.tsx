import type { Metadata } from "next";

import { SignInCard } from "@/components/sign-in/sign-in-card";

export const metadata: Metadata = {
  title: "Sign in",
};

export default function SignInPage() {
  return (
    <div className="container-page flex flex-1 items-center justify-center py-12 sm:py-20">
      <SignInCard />
    </div>
  );
}
