import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { authService } from "../services/authService";
import type { AuthUser } from "../types";

interface AuthState {
  user: AuthUser | null;
  ready: boolean;
  login: (email: string) => Promise<void>;
  register: (payload: { name: string; email: string; phone: string }) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    setUser(authService.current());
    setReady(true);
  }, []);

  const login = useCallback(async (email: string) => {
    setUser(await authService.login(email));
  }, []);

  const register = useCallback(async (payload: { name: string; email: string; phone: string }) => {
    setUser(await authService.register(payload));
  }, []);

  const logout = useCallback(() => {
    authService.logout();
    setUser(null);
  }, []);

  const value = useMemo<AuthState>(
    () => ({ user, ready, login, register, logout }),
    [user, ready, login, register, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
