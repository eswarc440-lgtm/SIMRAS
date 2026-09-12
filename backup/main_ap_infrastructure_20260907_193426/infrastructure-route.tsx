import { createFileRoute } from "@tanstack/react-router";
import { InfrastructurePage } from "../pages/infrastructure/InfrastructurePages";

export const Route = createFileRoute("/infrastructure/")({
  head: () => ({
    meta: [
      { title: "Infrastructure Assets — SIMRAS" },
      { name: "description", content: "Central register of monitored bridges, roads, buildings and utilities." },
      { property: "og:title", content: "Infrastructure Assets — SIMRAS" },
      { property: "og:description", content: "Central register of monitored bridges, roads, buildings and utilities." },
    ],
  }),
  component: InfrastructurePage,
});
