import { createFileRoute } from "@tanstack/react-router";
import { PublicNav } from "../components/navigation/PublicNav";
import { SiteFooter } from "../components/navigation/SiteFooter";
import { Hero } from "../components/landing/Hero";
import { PlatformIntro } from "../components/landing/PlatformIntro";
import { AISection } from "../components/landing/AISection";
import { DigitalTwinSection, GISSection } from "../components/landing/DigitalTwinSection";
import { Capabilities, HowItWorks, ImpactSection, MonitoringSection } from "../components/landing/Sections";
import { FinalCTA } from "../components/landing/FinalCTA";

const title = "SIMRAS â€” Structural Infrastructure Monitoring & Risk Intelligence";
const description =
  "SIMRAS combines AI risk prediction, GIS and digital twin technology to monitor structural infrastructure and support data-driven decisions.";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title },
      { name: "description", content: description },
      { property: "og:title", content: title },
      { property: "og:description", content: description },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: LandingPage,
});

function LandingPage() {
  return (
    <div className="min-h-screen bg-background">
      <PublicNav />
      <main>
        <Hero />
        <PlatformIntro />
        <AISection />
        <DigitalTwinSection />
        <GISSection />
        <HowItWorks />
        <Capabilities />
        <MonitoringSection />
        <ImpactSection />
        <FinalCTA />
      </main>
      <SiteFooter />
    </div>
  );
}

