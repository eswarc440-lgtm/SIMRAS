import { createFileRoute } from "@tanstack/react-router";
import { ProfilePage } from "../pages/settings/SettingsPages";

export const Route = createFileRoute("/profile")({
  head: () => ({
    meta: [
      { title: "Profile — SIMRAS" },
      { name: "description", content: "Your SIMRAS account, role and organisation details." },
      { property: "og:title", content: "Profile — SIMRAS" },
      { property: "og:description", content: "Your SIMRAS account, role and organisation details." },
    ],
  }),
  component: ProfilePage,
});
