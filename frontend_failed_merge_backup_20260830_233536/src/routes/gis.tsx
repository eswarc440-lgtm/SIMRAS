import { createFileRoute } from "@tanstack/react-router";
import { GISPage } from "../pages/gis/GISPage";

export const Route = createFileRoute("/gis")({
  head: () => ({
    meta: [
      { title: "GIS Mapping — SIMRAS" },
      { name: "description", content: "Geospatial view of monitored assets with live risk overlays." },
      { property: "og:title", content: "GIS Mapping — SIMRAS" },
      { property: "og:description", content: "Geospatial view of monitored assets with live risk overlays." },
    ],
  }),
  component: GISPage,
});
