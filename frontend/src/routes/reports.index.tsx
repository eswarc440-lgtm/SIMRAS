import { createFileRoute } from "@tanstack/react-router";
import { ReportsPage } from "../pages/reports/ReportsPages";

export const Route = createFileRoute("/reports/")({
  head: () => ({
    meta: [
      { title: "Reports — SIMRAS" },
      { name: "description", content: "Generated risk, condition, analytics and inspection reports." },
      { property: "og:title", content: "Reports — SIMRAS" },
      { property: "og:description", content: "Generated risk, condition, analytics and inspection reports." },
    ],
  }),
  component: ReportsPage,
});
