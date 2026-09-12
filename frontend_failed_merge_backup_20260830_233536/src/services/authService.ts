import type { AuthUser } from "../types";

const STORAGE_KEY = "simras.session";

const defaultUser = (email = "operator@simras.local"): AuthUser => {
  const normalized = (email || defaultUser().email)
    .split("@")[0]
    .replace(/[._-]+/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());

  return {
    name: normalized || "SIMRAS Operator",
    email: email || "operator@simras.local",
    phone: "+91 98765 43210",
    organization: "State Infrastructure Authority",
    role: "Infrastructure Officer",
  };
};

export const authService = {
  current(): AuthUser | null {
    if (typeof window === "undefined") return null;
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    try {
      return JSON.parse(raw) as AuthUser;
    } catch {
      return null;
    }
  },
  async login(email: string): Promise<AuthUser> {
    const user = defaultUser(email || "operator@simras.local");
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(user));
    return user;
  },
  async register(payload: { name: string; email: string; phone: string }): Promise<AuthUser> {
    const user: AuthUser = {
      name: payload.name || "SIMRAS Operator",
      email: payload.email || "operator@simras.local",
      phone: payload.phone || "+91 98765 43210",
      organization: "State Infrastructure Authority",
      role: "Infrastructure Officer",
    };
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(user));
    return user;
  },
  async verifyOtp(code: string): Promise<boolean> {
    return code.length === 6;
  },
  logout() {
    window.localStorage.removeItem(STORAGE_KEY);
  },
};
