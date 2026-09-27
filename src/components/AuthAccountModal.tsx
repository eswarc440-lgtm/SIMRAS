import React, { useEffect, useState } from "react";
import {
  X,
  UserPlus,
  Mail,
  Lock,
  KeyRound,
  BadgeCheck,
} from "lucide-react";

export type AuthFlowMode =
  | "create"
  | "forgot"
  | null;

interface Props {
  mode: AuthFlowMode;
  onClose: () => void;
  onRegistered: (user: any, token: string) => void;
}

export function AuthAccountModal({
  mode,
  onClose,
  onRegistered,
}: Props) {
  const [step, setStep] = useState<
    "email" | "code" | "reset" | "done"
  >("email");

  const [fullName, setFullName] = useState("");
  const [officerId, setOfficerId] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] =
    useState("");
  const [code, setCode] = useState("");
  const [resetToken, setResetToken] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] =
    useState<string | null>(null);
  const [message, setMessage] =
    useState<string | null>(null);

  useEffect(() => {
    setStep("email");
    setFullName("");
    setOfficerId("");
    setEmail("");
    setPassword("");
    setConfirmPassword("");
    setCode("");
    setResetToken("");
    setError(null);
    setMessage(null);
  }, [mode]);

  if (!mode) return null;

  const api = async (
    url: string,
    body: Record<string, unknown>,
  ) => {
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });

    const data = await response
      .json()
      .catch(() => ({}));

    if (!response.ok) {
      throw new Error(
        data.error ||
          data.detail ||
          `Request failed (${response.status})`,
      );
    }

    return data;
  };

  const createAccount = async (
    event: React.FormEvent,
  ) => {
    event.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const data = await api(
        "/api/v1/auth/register",
        {
          full_name: fullName,
          officer_id: officerId,
          email,
          password,
          confirm_password: confirmPassword,
        },
      );

      onRegistered(data.user, data.token);
      onClose();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to create account.",
      );
    } finally {
      setLoading(false);
    }
  };

  const requestCode = async (
    event: React.FormEvent,
  ) => {
    event.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const data = await api(
        "/api/v1/auth/forgot-password/request",
        { email },
      );

      setMessage(data.message);
      setStep("code");
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to send verification code.",
      );
    } finally {
      setLoading(false);
    }
  };

  const verifyCode = async (
    event: React.FormEvent,
  ) => {
    event.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const data = await api(
        "/api/v1/auth/forgot-password/verify",
        { email, code },
      );

      setResetToken(data.reset_token);
      setStep("reset");
      setMessage(
        "Email verification successful. Enter your new password.",
      );
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Verification failed.",
      );
    } finally {
      setLoading(false);
    }
  };

  const resetPassword = async (
    event: React.FormEvent,
  ) => {
    event.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const data = await api(
        "/api/v1/auth/forgot-password/reset",
        {
          email,
          reset_token: resetToken,
          password,
          confirm_password: confirmPassword,
        },
      );

      setMessage(data.message);
      setStep("done");
      setPassword("");
      setConfirmPassword("");
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Password reset failed.",
      );
    } finally {
      setLoading(false);
    }
  };

  const inputClass =
    "w-full px-3 py-2.5 border border-slate-300 rounded-md text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-[#1268A8] focus:border-[#1268A8]";

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-slate-950/65 backdrop-blur-sm p-4">
      <div className="w-full max-w-md rounded-xl bg-white shadow-2xl border border-slate-200 overflow-hidden">
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-200 bg-slate-50">
          <div className="flex items-center gap-2">
            {mode === "create" ? (
              <UserPlus className="w-5 h-5 text-[#1268A8]" />
            ) : (
              <KeyRound className="w-5 h-5 text-[#1268A8]" />
            )}

            <div>
              <h2 className="font-bold text-slate-900">
                {mode === "create"
                  ? "Create SIMRAS Account"
                  : "Reset Password"}
              </h2>
              <p className="text-[11px] text-slate-500">
                SIMRAS Officer Portal
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded hover:bg-slate-200 text-slate-500"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-5">
          {error && (
            <div className="mb-4 p-3 text-xs rounded-md bg-red-50 border border-red-200 text-red-700">
              {error}
            </div>
          )}

          {message && (
            <div className="mb-4 p-3 text-xs rounded-md bg-emerald-50 border border-emerald-200 text-emerald-700">
              {message}
            </div>
          )}

          {mode === "create" && (
            <form
              onSubmit={createAccount}
              className="space-y-3"
            >
              <div>
                <label className="text-xs font-semibold text-slate-700">
                  Full Name
                </label>
                <input
                  className={inputClass}
                  value={fullName}
                  onChange={(e) =>
                    setFullName(e.target.value)
                  }
                  required
                  autoComplete="name"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-700">
                  Officer ID
                </label>
                <input
                  className={inputClass}
                  value={officerId}
                  onChange={(e) =>
                    setOfficerId(e.target.value)
                  }
                  required
                  autoComplete="username"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-700">
                  Email Address
                </label>
                <div className="relative">
                  <Mail className="absolute left-3 top-3 w-4 h-4 text-slate-400" />
                  <input
                    type="email"
                    className={`${inputClass} pl-9`}
                    value={email}
                    onChange={(e) =>
                      setEmail(e.target.value)
                    }
                    required
                    autoComplete="email"
                  />
                </div>
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-700">
                  Password
                </label>
                <input
                  type="password"
                  className={inputClass}
                  value={password}
                  minLength={8}
                  onChange={(e) =>
                    setPassword(e.target.value)
                  }
                  required
                  autoComplete="new-password"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-700">
                  Confirm Password
                </label>
                <input
                  type="password"
                  className={inputClass}
                  value={confirmPassword}
                  minLength={8}
                  onChange={(e) =>
                    setConfirmPassword(e.target.value)
                  }
                  required
                  autoComplete="new-password"
                />
              </div>

              <button
                disabled={loading}
                className="w-full py-2.5 rounded-md bg-[#1268A8] hover:bg-[#0D4E7A] text-white text-sm font-bold disabled:opacity-50"
              >
                {loading
                  ? "Creating Account..."
                  : "Create Account"}
              </button>
            </form>
          )}

          {mode === "forgot" &&
            step === "email" && (
              <form
                onSubmit={requestCode}
                className="space-y-4"
              >
                <p className="text-sm text-slate-600">
                  Enter your registered email address.
                  SIMRAS will send a 6-digit verification
                  code to that email.
                </p>

                <input
                  type="email"
                  className={inputClass}
                  value={email}
                  placeholder="officer@example.com"
                  onChange={(e) =>
                    setEmail(e.target.value)
                  }
                  required
                  autoComplete="email"
                />

                <button
                  disabled={loading}
                  className="w-full py-2.5 rounded-md bg-[#1268A8] text-white text-sm font-bold disabled:opacity-50"
                >
                  {loading
                    ? "Sending Code..."
                    : "Send Verification Code"}
                </button>
              </form>
            )}

          {mode === "forgot" &&
            step === "code" && (
              <form
                onSubmit={verifyCode}
                className="space-y-4"
              >
                <p className="text-sm text-slate-600">
                  Enter the 6-digit code sent to{" "}
                  <strong>{email}</strong>.
                </p>

                <input
                  inputMode="numeric"
                  pattern="[0-9]{6}"
                  maxLength={6}
                  className={`${inputClass} text-center text-2xl tracking-[0.4em] font-bold`}
                  value={code}
                  onChange={(e) =>
                    setCode(
                      e.target.value
                        .replace(/\D/g, "")
                        .slice(0, 6),
                    )
                  }
                  required
                />

                <button
                  disabled={
                    loading || code.length !== 6
                  }
                  className="w-full py-2.5 rounded-md bg-[#1268A8] text-white text-sm font-bold disabled:opacity-50"
                >
                  {loading
                    ? "Verifying..."
                    : "Verify Code"}
                </button>
              </form>
            )}

          {mode === "forgot" &&
            step === "reset" && (
              <form
                onSubmit={resetPassword}
                className="space-y-4"
              >
                <div>
                  <label className="text-xs font-semibold text-slate-700">
                    New Password
                  </label>
                  <input
                    type="password"
                    className={inputClass}
                    value={password}
                    minLength={8}
                    onChange={(e) =>
                      setPassword(e.target.value)
                    }
                    required
                    autoComplete="new-password"
                  />
                </div>

                <div>
                  <label className="text-xs font-semibold text-slate-700">
                    Confirm New Password
                  </label>
                  <input
                    type="password"
                    className={inputClass}
                    value={confirmPassword}
                    minLength={8}
                    onChange={(e) =>
                      setConfirmPassword(
                        e.target.value,
                      )
                    }
                    required
                    autoComplete="new-password"
                  />
                </div>

                <button
                  disabled={loading}
                  className="w-full py-2.5 rounded-md bg-[#1268A8] text-white text-sm font-bold disabled:opacity-50"
                >
                  {loading
                    ? "Updating Password..."
                    : "Reset Password"}
                </button>
              </form>
            )}

          {mode === "forgot" &&
            step === "done" && (
              <div className="text-center py-5">
                <BadgeCheck className="w-12 h-12 text-emerald-600 mx-auto mb-3" />

                <h3 className="font-bold text-slate-900">
                  Password Updated
                </h3>

                <p className="text-sm text-slate-600 mt-2">
                  Your new password is active. Return
                  to the login form and sign in.
                </p>

                <button
                  type="button"
                  onClick={onClose}
                  className="mt-5 w-full py-2.5 rounded-md bg-[#1268A8] text-white text-sm font-bold"
                >
                  Return to Login
                </button>
              </div>
            )}
        </div>
      </div>
    </div>
  );
}