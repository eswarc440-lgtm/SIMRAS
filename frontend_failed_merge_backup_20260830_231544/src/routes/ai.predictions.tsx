import { createFileRoute } from "@tanstack/react-router";
import { PredictionsPage } from "../pages/ai/AIPages";

export const Route = createFileRoute("/ai/predictions")({
  head: () => ({
    meta: [
      { title: "AI Predictions — SIMRAS" },
      { name: "description", content: "Asset-level model predictions with confidence scores and risk levels." },
      { property: "og:title", content: "AI Predictions — SIMRAS" },
      { property: "og:description", content: "Asset-level model predictions with confidence scores and risk levels." },
    ],
  }),
  component: PredictionsPage,
});
