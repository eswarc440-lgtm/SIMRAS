import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate } from "@tanstack/react-router";
import { Loader2 } from "lucide-react";
import { AuthLayout } from "../../layouts/AuthLayout";
import { Button } from "../../components/ui/button";
import { InputOTP, InputOTPGroup, InputOTPSlot } from "../../components/ui/input-otp";
import { authService } from "../../services/authService";

export function OTPPage({ channel }: { channel: "email" | "phone" }) {
  const navigate = useNavigate();
  const [code, setCode] = useState("");
  const [seconds, setSeconds] = useState(45);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (seconds <= 0) return;
    const t = setTimeout(() => setSeconds((s) => s - 1), 1000);
    return () => clearTimeout(t);
  }, [seconds]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    const ok = await authService.verifyOtp(code);
    setLoading(false);
    if (!ok) {
      setError("Enter the complete 6-digit verification code.");
      return;
    }
    await authService.login("");
    navigate({ to: "/home" });
  }

  const target = channel === "email" ? "r.prasad@infra.gov.in" : "+91 98490 00000";

  return (
    <AuthLayout
      title={channel === "email" ? "Verify your email" : "Verify your phone"}
      description={`Enter the 6-digit verification code sent to ${target}.`}
      footer={
        <p>
          <Link to="/auth/login" className="font-medium text-primary underline underline-offset-4">
            Change {channel === "email" ? "email" : "phone number"}
          </Link>
        </p>
      }
    >
      <form onSubmit={onSubmit} className="space-y-6">
        <InputOTP maxLength={6} value={code} onChange={setCode} aria-label="Verification code">
          <InputOTPGroup>
            {[0, 1, 2, 3, 4, 5].map((i) => (
              <InputOTPSlot key={i} index={i} />
            ))}
          </InputOTPGroup>
        </InputOTP>

        {error && <p className="text-sm text-danger">{error}</p>}

        <Button type="submit" className="min-h-11 w-full" disabled={loading}>
          {loading && <Loader2 className="size-4 animate-spin" />}
          Verify &amp; Continue
        </Button>

        <div className="text-sm text-muted-foreground">
          {seconds > 0 ? (
            <span>Resend code in {seconds}s</span>
          ) : (
            <button type="button" onClick={() => setSeconds(45)} className="font-medium text-primary underline underline-offset-4">
              Resend OTP
            </button>
          )}
        </div>
      </form>
    </AuthLayout>
  );
}
