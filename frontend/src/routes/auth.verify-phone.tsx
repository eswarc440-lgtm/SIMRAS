import { createFileRoute } from "@tanstack/react-router";
import { OTPPage } from "../pages/auth/OTPPage";

export const Route = createFileRoute("/auth/verify-phone")({
  head: () => ({
    meta: [
      { title: "Verify Phone — SIMRAS" },
      { name: "description", content: "Confirm your phone number with a one-time verification code." },
      { property: "og:title", content: "Verify Phone — SIMRAS" },
      { property: "og:description", content: "Confirm your SIMRAS account phone number with a one-time code." },
    ],
  }),
  component: () => <OTPPage channel="phone" />,
});
