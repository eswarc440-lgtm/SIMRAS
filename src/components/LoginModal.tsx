import React, { useState } from "react";
import { X, ShieldCheck, Lock, User, AlertCircle } from "lucide-react";

interface UserProfile {
  id: string;
  email: string;
  name: string;
  role: "PUBLIC" | "OFFICER" | "REVIEWER" | "ADMIN";
  department: string;
}

interface LoginModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentUser: UserProfile | null;
  onLoginSuccess: (user: UserProfile, token: string) => void;
  onLogout: () => void;
}

export function LoginModal({ isOpen, onClose, currentUser, onLoginSuccess, onLogout }: LoginModalProps) {
  const [email, setEmail] = useState("officer@simras.gov.in");
  const [password, setPassword] = useState("Officer@123");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleLogin = async (e: React.FormEvent) => {
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
        throw new Error(data.error || "Authentication failed");
      }

      const { user, token } = await res.json();
      localStorage.setItem("simras_token", token);
      localStorage.setItem("simras_user", JSON.stringify(user));
      onLoginSuccess(user, token);
      onClose();
    } catch (err: any) {
      setError(err.message || "Failed to sign in");
    } finally {
      setLoading(false);
    }
  };

  const handleQuickSelect = (roleEmail: string, rolePass: string) => {
    setEmail(roleEmail);
    setPassword(rolePass);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="bg-[#0b1723] border border-cyan-500/30 rounded-xl max-w-md w-full p-6 shadow-2xl relative text-white">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-gray-400 hover:text-white transition"
          aria-label="Close"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-3 mb-5">
          <div className="w-10 h-10 rounded-lg bg-cyan-500/20 border border-cyan-400/40 flex items-center justify-center text-cyan-400">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-lg font-bold tracking-tight text-cyan-100">
              {currentUser ? "Officer Session" : "Official Authority Login"}
            </h2>
            <p className="text-xs text-gray-400">Government of Andhra Pradesh Disaster Authority</p>
          </div>
        </div>

        {currentUser ? (
          <div className="space-y-4">
            <div className="bg-[#122233] p-4 rounded-lg border border-cyan-500/20 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs text-gray-400">Authenticated User</span>
                <span className="text-xs font-semibold px-2 py-0.5 rounded bg-cyan-900/50 text-cyan-300 border border-cyan-500/30">
                  {currentUser.role}
                </span>
              </div>
              <p className="font-medium text-white">{currentUser.name}</p>
              <p className="text-xs text-gray-400">{currentUser.email}</p>
              <p className="text-xs text-cyan-400/80">{currentUser.department}</p>
            </div>

            <div className="flex gap-3">
              <button
                onClick={onLogout}
                className="flex-1 py-2 px-4 rounded-lg bg-red-950/60 border border-red-500/40 text-red-300 hover:bg-red-900/80 text-sm font-medium transition"
              >
                Sign Out
              </button>
              <button
                onClick={onClose}
                className="flex-1 py-2 px-4 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-black text-sm font-semibold transition"
              >
                Done
              </button>
            </div>
          </div>
        ) : (
          <div>
            {error && (
              <div className="mb-4 p-3 rounded-lg bg-red-950/50 border border-red-500/40 flex items-center gap-2 text-xs text-red-300">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <form onSubmit={handleLogin} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-gray-300 mb-1">Official Email ID</label>
                <div className="relative">
                  <User className="w-4 h-4 text-gray-400 absolute left-3 top-3" />
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full bg-[#122233] border border-gray-700 focus:border-cyan-400 rounded-lg pl-9 pr-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none"
                    placeholder="officer@simras.gov.in"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-300 mb-1">Security Password</label>
                <div className="relative">
                  <Lock className="w-4 h-4 text-gray-400 absolute left-3 top-3" />
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full bg-[#122233] border border-gray-700 focus:border-cyan-400 rounded-lg pl-9 pr-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none"
                    placeholder="••••••••"
                  />
                </div>
              </div>

              <div className="pt-1">
                <p className="text-[11px] text-gray-400 mb-2 font-medium">Quick Credentials Switcher:</p>
                <div className="grid grid-cols-3 gap-2">
                  <button
                    type="button"
                    onClick={() => handleQuickSelect("officer@simras.gov.in", "Officer@123")}
                    className="text-[11px] p-1.5 rounded bg-[#13273b] hover:bg-cyan-950/60 border border-gray-700 hover:border-cyan-500/40 text-cyan-300 text-center transition"
                  >
                    Field Officer
                  </button>
                  <button
                    type="button"
                    onClick={() => handleQuickSelect("reviewer@simras.gov.in", "Reviewer@123")}
                    className="text-[11px] p-1.5 rounded bg-[#13273b] hover:bg-cyan-950/60 border border-gray-700 hover:border-cyan-500/40 text-cyan-300 text-center transition"
                  >
                    Tech Reviewer
                  </button>
                  <button
                    type="button"
                    onClick={() => handleQuickSelect("admin@simras.gov.in", "Admin@123")}
                    className="text-[11px] p-1.5 rounded bg-[#13273b] hover:bg-cyan-950/60 border border-gray-700 hover:border-cyan-500/40 text-cyan-300 text-center transition"
                  >
                    Chief Admin
                  </button>
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full mt-2 py-2.5 px-4 rounded-lg bg-gradient-to-r from-cyan-400 to-cyan-500 hover:from-cyan-300 hover:to-cyan-400 text-black font-semibold text-sm shadow-lg shadow-cyan-500/20 transition disabled:opacity-50"
              >
                {loading ? "Authenticating..." : "Sign In to Authority Console"}
              </button>
            </form>
          </div>
        )}
      </div>
    </div>
  );
}
