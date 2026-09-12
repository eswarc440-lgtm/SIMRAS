import { createFileRoute } from "@tanstack/react-router";
import { MainInfrastructurePage } from "../pages/infrastructure/MainInfrastructurePage";

export const Route = createFileRoute("/infrastructure/")({
  head: () => ({
    meta: [
      {
        title:
          "Main Andhra Pradesh Infrastructure — SIMRAS",
      },
      {
        name: "description",
        content:
          "Main dams, barrages, bridges, airports and temples monitored by SIMRAS.",
      },
    ],
  }),
  component: MainInfrastructurePage,
});
