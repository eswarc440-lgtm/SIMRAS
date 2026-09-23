import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "@tanstack/react-router";
import { Loader2, Mail, Smartphone } from "lucide-react";
import { AuthLayout } from "../../layouts/AuthLayout";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Separator } from "../../components/ui/separator";
import { useAuth } from "../../hooks/useAuth";

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      await login(email);
      navigate({ to: "/home" });
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthLayout
      title="Welcome back to SIMRAS"
      description="Access your infrastructure intelligence platform."
      footer={
        <p>
          Don&apos;t have an account?{" "}
          <Link to="/auth/register" className="font-medium text-primary underline underline-offset-4">
            Create account
          </Link>
        </p>
      }
    >
      <form onSubmit={onSubmit} className="space-y-5">
        <div className="space-y-2">
          <Label htmlFor="login-email">Email</Label>
          <Input
            id="login-email"
            type="email"
            required
            autoComplete="email"
            placeholder="name@organisation.gov.in"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </div>
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label htmlFor="login-password">Password</Label>
            <Link to="/auth/forgot-password" className="text-xs text-muted-foreground underline underline-offset-4">
              Forgot password?
            </Link>
          </div>
          <Input
            id="login-password"
            type="password"
            required
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>

        <Button type="submit" className="min-h-11 w-full" disabled={loading}>
          {loading && <Loader2 className="size-4 animate-spin" />}
          Sign In
        </Button>
      </form>

      <div className="my-7 flex items-center gap-4">
        <Separator className="flex-1" />
        <span className="eyebrow text-muted-foreground">or</span>
        <Separator className="flex-1" />
      </div>

      <div className="grid gap-2">
        <Button asChild variant="outline" className="min-h-11 w-full">
          <Link to="/auth/verify-email">
            <Mail className="size-4" />
            Continue with Email OTP
          </Link>
        </Button>
        <Button asChild variant="outline" className="min-h-11 w-full">
          <Link to="/auth/verify-phone">
            <Smartphone className="size-4" />
            Continue with Phone OTP
          </Link>
        </Button>
      </div>
    </AuthLayout>
  );
}
