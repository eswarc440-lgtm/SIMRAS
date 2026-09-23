import { createFileRoute } from "@tanstack/react-router";
import { DashboardPage } from "../pages/dashboard/DashboardPage";

export const Route = createFileRoute("/dashboard")({
  head: () => ({
    meta: [
      { title: "SIMRAS Dashboard" },
      { name: "description", content: "Real-time infrastructure health, risk and AI insights across the monitored portfolio." },
      { property: "og:title", content: "SIMRAS Dashboard" },
      { property: "og:description", content: "Real-time infrastructure health, risk and AI insights across the monitored portfolio." },
    ],
  }),
  component: DashboardPage,
});
