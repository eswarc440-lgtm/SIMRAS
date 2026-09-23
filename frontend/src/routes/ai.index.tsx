import { createFileRoute } from "@tanstack/react-router";
import { AIOverviewPage } from "../pages/ai/AIPages";

export const Route = createFileRoute("/ai/")({
  head: () => ({
    meta: [
      { title: "AI Intelligence — SIMRAS" },
      { name: "description", content: "Predictive models scoring structural condition, degradation and failure risk." },
      { property: "og:title", content: "AI Intelligence — SIMRAS" },
      { property: "og:description", content: "Predictive models scoring structural condition, degradation and failure risk." },
    ],
  }),
  component: AIOverviewPage,
});
