import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "@tanstack/react-router";
import { Loader2 } from "lucide-react";
import { AuthLayout } from "../../layouts/AuthLayout";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { useAuth } from "../../hooks/useAuth";

export function RegisterPage() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: "", email: "", phone: "", password: "", confirm: "" });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const set = (key: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [key]: e.target.value }));

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (form.password !== form.confirm) {
      setError("Passwords do not match.");
      return;
    }
    setError("");
    setLoading(true);
    await register({ name: form.name, email: form.email, phone: form.phone });
    navigate({ to: "/auth/verify-email" });
  }

  return (
    <AuthLayout
      title="Create your SIMRAS account"
      description="Register to access infrastructure monitoring and risk intelligence."
      footer={
        <p>
          Already registered?{" "}
          <Link to="/auth/login" className="font-medium text-primary underline underline-offset-4">
            Sign in
          </Link>
        </p>
      }
    >
      <form onSubmit={onSubmit} className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="reg-name">Full Name</Label>
          <Input id="reg-name" required autoComplete="name" value={form.name} onChange={set("name")} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="reg-email">Email</Label>
          <Input id="reg-email" type="email" required autoComplete="email" value={form.email} onChange={set("email")} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="reg-phone">Phone Number</Label>
          <Input id="reg-phone" type="tel" required autoComplete="tel" value={form.phone} onChange={set("phone")} />
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor="reg-password">Password</Label>
            <Input id="reg-password" type="password" required value={form.password} onChange={set("password")} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="reg-confirm">Confirm Password</Label>
            <Input id="reg-confirm" type="password" required value={form.confirm} onChange={set("confirm")} />
          </div>
        </div>

        {error && <p className="text-sm text-danger">{error}</p>}

        <Button type="submit" className="min-h-11 w-full" disabled={loading}>
          {loading && <Loader2 className="size-4 animate-spin" />}
          Create Account
        </Button>
      </form>
    </AuthLayout>
  );
}
