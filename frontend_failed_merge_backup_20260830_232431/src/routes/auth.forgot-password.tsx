import { createFileRoute } from "@tanstack/react-router";
import { ForgotPasswordPage } from "../pages/auth/PasswordPages";

export const Route = createFileRoute("/auth/forgot-password")({
  head: () => ({
    meta: [
      { title: "Forgot Password — SIMRAS" },
      { name: "description", content: "Recover access to your SIMRAS infrastructure intelligence account." },
      { property: "og:title", content: "Forgot Password — SIMRAS" },
      { property: "og:description", content: "Recover access to your SIMRAS account." },
    ],
  }),
  component: ForgotPasswordPage,
});
