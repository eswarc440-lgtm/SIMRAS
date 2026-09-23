import { useState } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import './LoginPage.css';

interface LoginPageProps {
  onLoginComplete?: () => void;
  onSignupClick?: () => void;
  onForgotPasswordClick?: () => void;
}

export function LoginPage({ onLoginComplete, onSignupClick, onForgotPasswordClick }: LoginPageProps) {
  const { login } = useAuth();
  
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      await login(email, password);
      // Call the callback to navigate to dashboard
      onLoginComplete?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-container">
        {/* Left side - Branding */}
        <div className="login-branding">
          <div className="branding-content">
            <div className="logo-section">
              <div className="logo-icon">🏗️</div>
              <h1>SIMRAS</h1>
            </div>
            <p className="tagline">Smart Infrastructure Monitoring & Risk Assistance System</p>
            <div className="benefits">
              <div className="benefit-item">
                <span className="check-icon">✓</span>
                <span>Real-time infrastructure monitoring</span>
              </div>
              <div className="benefit-item">
                <span className="check-icon">✓</span>
                <span>Risk-based asset management</span>
              </div>
              <div className="benefit-item">
                <span className="check-icon">✓</span>
                <span>Digital twin visualization</span>
              </div>
              <div className="benefit-item">
                <span className="check-icon">✓</span>
                <span>Integrated workflow management</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right side - Login form */}
        <div className="login-form-section">
          <div className="form-container">
            <h2>Officer Portal</h2>
            <p className="form-subtitle">Sign in to your account</p>

            {error && (
              <div className="error-alert">
                <span className="error-icon">⚠️</span>
                <span>{error}</span>
              </div>
            )}

            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label htmlFor="email">Officer ID or Email</label>
                <input
                  id="email"
                  type="text"
                  placeholder="your.email@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={loading}
                  required
                />
              </div>

              <div className="form-group">
                <label htmlFor="password">Password</label>
                <input
                  id="password"
                  type="password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={loading}
                  required
                />
              </div>

              <button 
                type="submit" 
                className="sign-in-button"
                disabled={loading}
              >
                {loading ? 'Signing in...' : 'Sign In'}
              </button>
            </form>

            <div className="form-footer">
              <button 
                type="button"
                onClick={onForgotPasswordClick}
                className="forgot-password-link"
              >
                Forgot password?
              </button>
            </div>

            <div className="auth-links">
              <p className="signup-prompt">
                Don't have an account?{' '}
                <button 
                  type="button"
                  onClick={onSignupClick}
                  className="signup-link"
                >
                  Create one
                </button>
              </p>
            </div>

            <div className="demo-notice">
              <p className="notice-title">Demo Credentials</p>
              <div className="demo-credentials">
                <div className="demo-user">
                  <strong>Officer:</strong> officer@demo.com / demo123
                </div>
                <div className="demo-user">
                  <strong>Reviewer:</strong> reviewer@demo.com / demo123
                </div>
                <div className="demo-user">
                  <strong>Admin:</strong> admin@demo.com / demo123
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="login-footer">
        <p>&copy; 2026 SIMRAS. Government of Andhra Pradesh.</p>
      </footer>
    </div>
  );
}
