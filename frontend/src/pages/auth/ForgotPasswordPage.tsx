import { useState } from 'react';
import './LoginPage.css';

interface ForgotPasswordPageProps {
  onResetSent?: () => void;
  onBackToLogin?: () => void;
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

export function ForgotPasswordPage({ onResetSent, onBackToLogin }: ForgotPasswordPageProps) {
  const [email, setEmail] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!email.trim()) {
      setError('Email is required');
      return;
    }

    if (!email.includes('@')) {
      setError('Invalid email address');
      return;
    }

    setLoading(true);

    try {
      // Call backend API to request password reset
      const response = await fetch(`${API_BASE_URL}/auth/forgot-password`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email }),
      });

      if (response.ok) {
        setSuccess(true);
        setEmail('');
        
        // Redirect after showing success message
        setTimeout(() => {
          onResetSent?.();
        }, 3000);
      } else {
        try {
          const data = await response.json();
          setError(data.detail || 'Failed to send reset link. Please check your email and try again.');
        } catch {
          setError(`Server error (${response.status}): ${response.statusText}`);
        }
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to send password reset link';
      // Check if it's a network error
      if (message.includes('Failed to fetch')) {
        setError('Cannot reach server. Please ensure backend is running at ' + API_BASE_URL);
      } else {
        setError(message);
      }
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

        {/* Right side - Forgot password form */}
        <div className="login-form-section">
          <div className="form-container">
            <h2>Reset Your Password</h2>
            <p className="form-subtitle">Enter your email to receive a reset link</p>

            {error && (
              <div className="error-alert">
                <span className="error-icon">⚠️</span>
                <span>{error}</span>
              </div>
            )}

            {success && (
              <div className="success-alert">
                <span className="success-icon">✓</span>
                <div>
                  <p className="font-bold">Password reset link sent!</p>
                  <p className="text-sm">Check your email for instructions to reset your password. Redirecting to login...</p>
                </div>
              </div>
            )}

            {!success && (
              <form onSubmit={handleSubmit}>
                <div className="form-group">
                  <label htmlFor="email">Email Address *</label>
                  <input
                    id="email"
                    type="email"
                    placeholder="your.email@example.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    disabled={loading}
                    required
                  />
                </div>

                <p className="form-hint">
                  We'll send you an email with a link to reset your password within 15 minutes.
                </p>

                <button 
                  type="submit" 
                  className="sign-in-button"
                  disabled={loading}
                >
                  {loading ? 'Sending...' : 'Send Reset Link'}
                </button>
              </form>
            )}

            <div className="form-footer">
              <button 
                type="button"
                onClick={onBackToLogin}
                className="forgot-password-link"
              >
                Back to login
              </button>
            </div>

            <div className="demo-notice">
              <p className="notice-title">Need Help?</p>
              <p className="notice-text">
                If you don't receive an email, check your spam folder or contact your administrator.
              </p>
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
