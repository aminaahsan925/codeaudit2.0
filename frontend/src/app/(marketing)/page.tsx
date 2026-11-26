import { ChecksBento } from "@/components/marketing/checks-bento";
import { ExampleReport } from "@/components/marketing/example-report";
import { Faq } from "@/components/marketing/faq";
import { FinalCta } from "@/components/marketing/final-cta";
import { Hero } from "@/components/marketing/hero";
import { HowItWorks } from "@/components/marketing/how-it-works";
import { TrustStrip } from "@/components/marketing/trust-strip";

export default function HomePage() {
  return (
    <>
      <Hero />
      <TrustStrip />
      <ChecksBento />
      <HowItWorks />
      <ExampleReport />
      <Faq />
      <FinalCta />
    </>
  );
}
