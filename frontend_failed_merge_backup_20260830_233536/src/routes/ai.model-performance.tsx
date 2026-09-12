import { createFileRoute } from "@tanstack/react-router";
import { ModelPerformancePage } from "../pages/ai/AIPages";

export const Route = createFileRoute("/ai/model-performance")({
  head: () => ({
    meta: [
      { title: "Model Performance — SIMRAS" },
      { name: "description", content: "Accuracy, precision and recall metrics for deployed SIMRAS models." },
      { property: "og:title", content: "Model Performance — SIMRAS" },
      { property: "og:description", content: "Accuracy, precision and recall metrics for deployed SIMRAS models." },
    ],
  }),
  component: ModelPerformancePage,
});
