import { createFileRoute } from "@tanstack/react-router";
import { AssetHistoryPage } from "../pages/infrastructure/InfrastructurePages";

export const Route = createFileRoute("/infrastructure/$id/history")({
  head: () => ({
    meta: [
      { title: "Inspection History — SIMRAS" },
      { name: "description", content: "Complete field inspection record for a monitored asset." },
      { property: "og:title", content: "Inspection History — SIMRAS" },
      { property: "og:description", content: "Complete field inspection record for a monitored asset." },
    ],
  }),
  component: RouteComponent,
});

function RouteComponent() {
  const { id } = Route.useParams();
  return <AssetHistoryPage id={id} />;
}
