import { createFileRoute } from "@tanstack/react-router";
import { LoginPage } from "../pages/auth/LoginPage";

export const Route = createFileRoute("/auth/login")({
  head: () => ({
    meta: [
      { title: "Sign In — SIMRAS" },
      { name: "description", content: "Sign in to the SIMRAS infrastructure monitoring and risk intelligence platform." },
      { property: "og:title", content: "Sign In — SIMRAS" },
      { property: "og:description", content: "Access your SIMRAS infrastructure intelligence workspace." },
    ],
  }),
  component: LoginPage,
});
