import { createFileRoute } from "@tanstack/react-router";
import { RiskAnalysisPage } from "../pages/ai/AIPages";

export const Route = createFileRoute("/ai/risk-analysis")({
  head: () => ({
    meta: [
      { title: "Risk Analysis — SIMRAS" },
      { name: "description", content: "Portfolio risk distribution, drivers and escalation priorities." },
      { property: "og:title", content: "Risk Analysis — SIMRAS" },
      { property: "og:description", content: "Portfolio risk distribution, drivers and escalation priorities." },
    ],
  }),
  component: RiskAnalysisPage,
});
