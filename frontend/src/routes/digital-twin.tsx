import { createFileRoute } from "@tanstack/react-router";
import { DigitalTwinPage } from "../pages/digital-twin/DigitalTwinPage";

export const Route = createFileRoute("/digital-twin")({
  head: () => ({
    meta: [
      { title: "Digital Twin — SIMRAS" },
      { name: "description", content: "Interactive structural twin workspace with sensor and model layers." },
      { property: "og:title", content: "Digital Twin — SIMRAS" },
      { property: "og:description", content: "Interactive structural twin workspace with sensor and model layers." },
    ],
  }),
  component: DigitalTwinPage,
});
