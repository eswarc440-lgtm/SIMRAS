import { createFileRoute } from "@tanstack/react-router";
import { HomePage } from "../pages/home/HomePage";

const title = "SIMRAS Home — Infrastructure & AI Intelligence";
const description =
  "Your SIMRAS gateway: monitor infrastructure health, assess structural risks and access AI-powered intelligence.";

export const Route = createFileRoute("/home")({
  head: () => ({
    meta: [
      { title },
      { name: "description", content: description },
      { property: "og:title", content: title },
      { property: "og:description", content: description },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: HomePage,
});
