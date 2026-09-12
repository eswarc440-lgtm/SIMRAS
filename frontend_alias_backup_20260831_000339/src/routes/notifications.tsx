import { createFileRoute } from "@tanstack/react-router";
import { NotificationsPage } from "../pages/notifications/NotificationsPage";

export const Route = createFileRoute("/notifications")({
  head: () => ({
    meta: [
      { title: "Notifications — SIMRAS" },
      { name: "description", content: "Risk alerts, inspection reminders and platform updates." },
      { property: "og:title", content: "Notifications — SIMRAS" },
      { property: "og:description", content: "Risk alerts, inspection reminders and platform updates." },
    ],
  }),
  component: NotificationsPage,
});
