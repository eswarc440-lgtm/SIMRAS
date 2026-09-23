import { useAuth } from '../contexts/AuthContext';
import { PublicHeader } from '../components/navigation/PublicHeader';
import { OfficerHeader } from '../components/navigation/OfficerHeader';
import { ReactNode } from 'react';

interface RootLayoutProps {
  children: ReactNode;
}

/**
 * Root layout that renders appropriate header based on authentication state
 */
export function RootLayout({ children }: RootLayoutProps) {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div style={{ 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center', 
        height: '100vh',
        background: '#f5f7fa',
        fontFamily: 'system-ui, sans-serif'
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 24, marginBottom: 16 }}>Loading...</div>
          <div style={{ color: '#666' }}>Initializing SIMRAS platform</div>
        </div>
      </div>
    );
  }

  return (
    <>
      {children}
    </>
  );
}
