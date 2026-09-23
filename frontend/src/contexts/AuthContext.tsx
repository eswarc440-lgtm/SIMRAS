import { createContext, useContext, useState, useEffect, ReactNode } from 'react';

interface User {
  id: number;
  officer_id: string;
  name: string;
  email: string;
  role: string;
  department: string | null;
  designation: string | null;
  district: string | null;
  phone: string | null;
  is_active: boolean;
  last_login: string | null;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  isAuthenticated: boolean;
  isOfficer: boolean;
  isReviewer: boolean;
  isAdmin: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Mock user for development/testing when auth is unavailable
const MOCK_USER: User = {
  id: 1,
  officer_id: "AP_DEMO_001",
  name: "Demo Officer",
  email: "officer@demo.com",
  role: "OFFICER",
  department: "Infrastructure Ministry",
  designation: "Inspector",
  district: "Andhra Pradesh",
  phone: "9876543210",
  is_active: true,
  last_login: new Date().toISOString(),
};

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [useMockAuth] = useState(() => {
    // Enable mock auth if env var set or always in development
    return import.meta.env.VITE_MOCK_AUTH === 'true' || import.meta.env.DEV;
  });

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    try {
      const response = await fetch('/api/v1/auth/me', {
        credentials: 'include',
      });
      if (response.ok) {
        const userData = await response.json();
        setUser(userData);
      } else if (useMockAuth) {
        // Fallback to mock user if auth endpoint fails and mock auth is enabled
        console.log('📋 Using mock officer for development');
        setUser(MOCK_USER);
      }
    } catch (error) {
      console.error('Auth check failed:', error);
      if (useMockAuth) {
        console.log('📋 Using mock officer for development');
        setUser(MOCK_USER);
      }
    } finally {
      setLoading(false);
    }
  };

  const login = async (email: string, password: string) => {
    if (useMockAuth && email === 'officer@demo.com') {
      // Mock login
      setUser(MOCK_USER);
      return;
    }

    const response = await fetch('/api/v1/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ email, password }),
    });

    if (!response.ok) {
      const data = await response.json();
      throw new Error(data.detail || 'Login failed');
    }

    const data = await response.json();
    setUser(data.user);
  };

  const logout = async () => {
    try {
      await fetch('/api/v1/auth/logout', {
        method: 'POST',
        credentials: 'include',
      });
    } catch {
      // Ignore logout errors in mock mode
    }
    setUser(null);
  };

  const value: AuthContextType = {
    user,
    loading,
    login,
    logout,
    isAuthenticated: !!user,
    isOfficer: user?.role === 'OFFICER' || user?.role === 'REVIEWER' || user?.role === 'ADMIN',
    isReviewer: user?.role === 'REVIEWER' || user?.role === 'ADMIN',
    isAdmin: user?.role === 'ADMIN',
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
