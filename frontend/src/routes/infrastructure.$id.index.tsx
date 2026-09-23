import { createFileRoute } from "@tanstack/react-router";
import { AssetDetailsPage } from "../pages/infrastructure/InfrastructurePages";

export const Route = createFileRoute("/infrastructure/$id/")({
  head: () => ({
    meta: [
      { title: "Asset Details — SIMRAS" },
      { name: "description", content: "Condition, risk, AI prediction and inspection record for a monitored asset." },
      { property: "og:title", content: "Asset Details — SIMRAS" },
      { property: "og:description", content: "Condition, risk, AI prediction and inspection record for a monitored asset." },
    ],
  }),
  component: RouteComponent,
});

function RouteComponent() {
  const { id } = Route.useParams();
  return <AssetDetailsPage id={id} />;
}
