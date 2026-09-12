import { createFileRoute } from "@tanstack/react-router";
import { AnalyticsPage } from "../pages/ai/AnalyticsPage";

export const Route = createFileRoute("/ai/analytics")({
  head: () => ({
    meta: [
      { title: "Analytics — SIMRAS" },
      { name: "description", content: "Condition trends, regional comparison and infrastructure analytics." },
      { property: "og:title", content: "Analytics — SIMRAS" },
      { property: "og:description", content: "Condition trends, regional comparison and infrastructure analytics." },
    ],
  }),
  component: AnalyticsPage,
});
