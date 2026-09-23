import { createFileRoute } from "@tanstack/react-router";
import { SettingsPage } from "../pages/settings/SettingsPages";

export const Route = createFileRoute("/settings")({
  head: () => ({
    meta: [
      { title: "Settings — SIMRAS" },
      { name: "description", content: "Account, security, notification and appearance preferences." },
      { property: "og:title", content: "Settings — SIMRAS" },
      { property: "og:description", content: "Account, security, notification and appearance preferences." },
    ],
  }),
  component: SettingsPage,
});
