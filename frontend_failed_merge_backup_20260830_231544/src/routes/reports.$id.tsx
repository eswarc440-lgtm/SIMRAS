import { createFileRoute } from "@tanstack/react-router";
import { ReportDetailsPage } from "../pages/reports/ReportsPages";

export const Route = createFileRoute("/reports/$id")({
  head: () => ({
    meta: [
      { title: "Report Details — SIMRAS" },
      { name: "description", content: "View a generated SIMRAS infrastructure report." },
      { property: "og:title", content: "Report Details — SIMRAS" },
      { property: "og:description", content: "View a generated SIMRAS infrastructure report." },
    ],
  }),
  component: RouteComponent,
});

function RouteComponent() {
  const { id } = Route.useParams();
  return <ReportDetailsPage id={id} />;
}
