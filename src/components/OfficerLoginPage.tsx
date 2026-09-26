import React, { useState } from "react";
import { Shield, Lock, User, CheckCircle2, ArrowRight, AlertCircle, ArrowLeft } from "lucide-react";


interface OfficerLoginPageProps {
  onLoginSuccess: (user: any, token: string) => void;
  onBackToPublic: () => void;
}

export function OfficerLoginPage({
  onLoginSuccess,
  onBackToPublic,
}: OfficerLoginPageProps) {
  const [email, setEmail] = useState("officer@simras.gov.in");
  const [password, setPassword] = useState("Officer@123");
  const [rememberMe, setRememberMe] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const res = await fetch("/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.error || "Authentication failed. Please verify credentials.");
      }

      const { user, token } = await res.json();
      localStorage.setItem("simras_token", token);
      localStorage.setItem("simras_user", JSON.stringify(user));
      onLoginSuccess(user, token);
    } catch (err: any) {
      setError(err.message || "Failed to authenticate session.");
    } finally {
      setLoading(false);
    }
  };

  const setRolePreset = (roleEmail: string, rolePass: string) => {
    setEmail(roleEmail);
    setPassword(rolePass);
  };

  return (
    <div className="min-h-screen flex bg-white font-sans text-slate-800">
      {/* LEFT COLUMN: Clean Government Login Form */}
      <div className="w-full lg:w-1/2 flex flex-col justify-between p-6 sm:p-12 lg:p-16">
        {/* Back to Citizen Portal */}
        <div>
          <button
            onClick={onBackToPublic}
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-[#1268A8] transition mb-8"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Return to Public Portal</span>
          </button>

          <div className="max-w-md mx-auto">
            {/* Government Emblem & Title */}
            <div className="flex items-center gap-3 mb-6">
              <img src="/images/ap-government-emblem.png" alt="Andhra Pradesh Government emblem" className="w-12 h-12 object-contain" />
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-2xl font-bold tracking-tight text-slate-900">SIMRAS</span>
                  <span className="text-xs font-bold px-2 py-0.5 rounded bg-[#1268A8] text-white uppercase tracking-wider">
                    Officer Portal
                  </span>
                </div>
                <p className="text-xs text-slate-500 mt-0.5">
                  Government of Andhra Pradesh ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ Infrastructure Operations
                </p>
              </div>
            </div>

            <div className="mb-6">
              <h1 className="text-xl sm:text-2xl font-bold text-slate-900">
                Secure Access for Authorized Personnel
              </h1>
              <p className="text-xs sm:text-sm text-slate-500 mt-1">
                Enter your credentials or authorized digital signature to access operational dashboards, inspection logs, and asset workflows.
              </p>
            </div>

            {error && (
              <div className="mb-4 p-3 rounded-md bg-red-50 border border-red-200 text-xs text-red-700 flex items-start gap-2">
                <AlertCircle className="w-4 h-4 text-red-500 shrink-0 mt-0.5" />
                <span>{error}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Officer ID / Email Address
                </label>
                <div className="relative">
                  <User className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="officer@simras.gov.in"
                    className="w-full pl-9 pr-3 py-2 text-sm bg-white border border-[#D8E2EA] rounded-md text-slate-900 focus:outline-none focus:ring-2 focus:ring-[#1268A8] focus:border-[#1268A8]"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Secure Password
                </label>
                <div className="relative">
                  <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢"
                    className="w-full pl-9 pr-3 py-2 text-sm bg-white border border-[#D8E2EA] rounded-md text-slate-900 focus:outline-none focus:ring-2 focus:ring-[#1268A8] focus:border-[#1268A8]"
                  />
                </div>
              </div>

              <div className="flex items-center justify-between text-xs pt-1">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                    className="rounded text-[#1268A8] focus:ring-[#1268A8]"
                  />
                  <span className="text-slate-600">Remember credentials on this device</span>
                </label>

                <button
                  type="button"
                  onClick={() => alert("Password reset instructions have been dispatched to your registered department email.")}
                  className="font-semibold text-[#1268A8] hover:underline"
                >
                  Forgot Password?
                </button>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full mt-2 py-2.5 px-4 bg-[#1268A8] hover:bg-[#0D4E7A] text-white text-sm font-bold rounded-md shadow-sm transition flex items-center justify-center gap-2 disabled:opacity-50"
              >
                {loading ? (
                  <span className="flex items-center gap-2">
                    <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    Authenticating Session...
                  </span>
                ) : (
                  <>
                    <span>Sign In to Officer Portal</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </form>

            {/* Quick Demo Role Selector */}
            <div className="mt-8 pt-6 border-t border-slate-200">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 block mb-2">
                Fast Login Role Presets (Government Sandbox):
              </span>
              <div className="grid grid-cols-3 gap-2">
                <button
                  type="button"
                  onClick={() => setRolePreset("officer@simras.gov.in", "Officer@123")}
                  className="px-2.5 py-1.5 rounded text-[11px] font-semibold border border-slate-200 hover:bg-slate-50 text-slate-700 text-center"
                >
                  Executive Engineer
                </button>
                <button
                  type="button"
                  onClick={() => setRolePreset("reviewer@simras.gov.in", "Reviewer@123")}
                  className="px-2.5 py-1.5 rounded text-[11px] font-semibold border border-slate-200 hover:bg-slate-50 text-slate-700 text-center"
                >
                  State Reviewer
                </button>
                <button
                  type="button"
                  onClick={() => setRolePreset("admin@simras.gov.in", "Admin@123")}
                  className="px-2.5 py-1.5 rounded text-[11px] font-semibold border border-slate-200 hover:bg-slate-50 text-slate-700 text-center"
                >
                  Super Admin
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Security Notice Footer */}
        <div className="text-center text-[11px] text-slate-400 mt-8">
          Restricted access system. Unauthorized access attempts are monitored and logged under the Information Technology Act.
        </div>
      </div>

      {/* RIGHT COLUMN: Large Infrastructure Visual with Reference Slogan */}
      <div className="hidden lg:flex lg:w-1/2 relative bg-[#0B3B63] overflow-hidden items-center justify-center text-white">
        <div className="absolute inset-0">
          <img
            src="/images/officer-login-bg.png"
            alt="Andhra Pradesh Infrastructure"
            className="w-full h-full object-cover opacity-100"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-[#061F35]/80 via-[#0B3B63]/45 to-[#0D4E7A]/55" />
        </div>

        <div className="relative z-10 max-w-lg p-12 text-center">
          <div className="inline-flex items-center justify-center p-3 rounded-full bg-white/10 backdrop-blur-md mb-6 border border-white/20">
            <Shield className="w-8 h-8 text-sky-300" />
          </div>

          <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-white leading-tight">
            Manage. Monitor. Maintain.
          </h2>
          <p className="text-xl sm:text-2xl font-bold text-sky-200 mt-2">
            A Safer Tomorrow.
          </p>

          <p className="text-sm text-slate-200 mt-6 leading-relaxed">
            Delivering 24/7 continuous structural surveillance, hydrologic monitoring, and evidence-verified maintenance workflows across Andhra Pradesh's vital dams, barrages, bridges, and transport gateways.
          </p>

          <div className="mt-8 inline-flex items-center gap-2 text-xs font-semibold px-4 py-2 rounded-full bg-sky-950/60 border border-sky-400/30 text-sky-300">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            <span>ISO 55001 Asset Management & CWC Guidelines Compliant</span>
          </div>
        </div>
      </div>
    </div>
  );
}
