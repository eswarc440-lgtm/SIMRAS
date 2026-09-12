import { createFileRoute } from "@tanstack/react-router";
import { ResetPasswordPage } from "../pages/auth/PasswordPages";

export const Route = createFileRoute("/auth/reset-password")({
  head: () => ({
    meta: [
      { title: "Reset Password — SIMRAS" },
      { name: "description", content: "Set a new password for your SIMRAS account." },
      { property: "og:title", content: "Reset Password — SIMRAS" },
      { property: "og:description", content: "Set a new password for your SIMRAS account." },
    ],
  }),
  component: ResetPasswordPage,
});
