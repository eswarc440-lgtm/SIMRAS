import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "@tanstack/react-router";
import { AuthLayout } from "../../layouts/AuthLayout";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";

export function ForgotPasswordPage() {
  const navigate = useNavigate();
  const [sent, setSent] = useState(false);

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    setSent(true);
    setTimeout(() => navigate({ to: "/auth/reset-password" }), 900);
  }

  return (
    <AuthLayout
      title="Reset your access"
      description="Enter the email registered with your SIMRAS account and we will send a recovery link."
      footer={
        <p>
          Remembered it?{" "}
          <Link to="/auth/login" className="font-medium text-primary underline underline-offset-4">
            Back to sign in
          </Link>
        </p>
      }
    >
      <form onSubmit={onSubmit} className="space-y-5">
        <div className="space-y-2">
          <Label htmlFor="fp-email">Email</Label>
          <Input id="fp-email" type="email" required autoComplete="email" />
        </div>
        <Button type="submit" className="min-h-11 w-full">
          Send Recovery Link
        </Button>
        {sent && <p className="text-sm text-success">Recovery link sent. Redirecting…</p>}
      </form>
    </AuthLayout>
  );
}

export function ResetPasswordPage() {
  const navigate = useNavigate();
  const [error, setError] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (password !== confirm) {
      setError("Passwords do not match.");
      return;
    }
    navigate({ to: "/auth/login" });
  }

  return (
    <AuthLayout title="Set a new password" description="Choose a strong password for your SIMRAS account.">
      <form onSubmit={onSubmit} className="space-y-5">
        <div className="space-y-2">
          <Label htmlFor="rp-password">New Password</Label>
          <Input
            id="rp-password"
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="rp-confirm">Confirm Password</Label>
          <Input id="rp-confirm" type="password" required value={confirm} onChange={(e) => setConfirm(e.target.value)} />
        </div>
        {error && <p className="text-sm text-danger">{error}</p>}
        <Button type="submit" className="min-h-11 w-full">
          Update Password
        </Button>
      </form>
    </AuthLayout>
  );
}
