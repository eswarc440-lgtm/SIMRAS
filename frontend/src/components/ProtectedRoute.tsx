import { useAuth } from '../contexts/AuthContext';
import { ReactNode } from 'react';

interface ProtectedRouteProps {
  children: ReactNode;
  requiresRole?: 'OFFICER' | 'REVIEWER' | 'ADMIN';
}

/**
 * Protects components that require authentication
 */
export function ProtectedRoute({ children, requiresRole }: ProtectedRouteProps) {
  const { isAuthenticated, user, loading } = useAuth();

  if (loading) {
    return <div>Loading...</div>;
  }

  if (!isAuthenticated) {
    return <div>Please log in to access this page.</div>;
  }

  if (requiresRole && user?.role !== requiresRole) {
    return <div>You do not have permission to access this page.</div>;
  }

  return <>{children}</>;
}
