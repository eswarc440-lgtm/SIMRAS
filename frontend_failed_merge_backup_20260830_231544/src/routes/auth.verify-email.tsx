import { createFileRoute } from "@tanstack/react-router";
import { OTPPage } from "../pages/auth/OTPPage";

export const Route = createFileRoute("/auth/verify-email")({
  head: () => ({
    meta: [
      { title: "Verify Email — SIMRAS" },
      { name: "description", content: "Confirm your email address with a one-time verification code." },
      { property: "og:title", content: "Verify Email — SIMRAS" },
      { property: "og:description", content: "Confirm your SIMRAS account email with a one-time code." },
    ],
  }),
  component: () => <OTPPage channel="email" />,
});
