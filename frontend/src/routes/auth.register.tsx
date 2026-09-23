import { createFileRoute } from "@tanstack/react-router";
import { RegisterPage } from "../pages/auth/RegisterPage";

export const Route = createFileRoute("/auth/register")({
  head: () => ({
    meta: [
      { title: "Create Account — SIMRAS" },
      { name: "description", content: "Register for SIMRAS structural infrastructure monitoring and risk assistance." },
      { property: "og:title", content: "Create Account — SIMRAS" },
      { property: "og:description", content: "Register for SIMRAS infrastructure intelligence access." },
    ],
  }),
  component: RegisterPage,
});
