import { useState, useEffect } from 'react';
import './LoginPage.css';

interface ResetPasswordPageProps {
  onResetComplete?: () => void;
  token?: string;
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

export function ResetPasswordPage({ onResetComplete, token }: ResetPasswordPageProps) {
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [resetToken, setResetToken] = useState(token || '');
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);
  const [tokenValid, setTokenValid] = useState(!token ? false : true);

  // Get token from URL query params if not provided as prop
  useEffect(() => {
    if (!token) {
      const params = new URLSearchParams(window.location.search);
      const urlToken = params.get('token');
      if (urlToken) {
        setResetToken(urlToken);
        setTokenValid(true);
      } else {
        setError('Invalid or missing reset token. Please request a new password reset link.');
      }
    }
  }, [token]);

  const validateForm = () => {
    if (!password.trim()) return 'New password is required';
    if (password.length < 8) return 'Password must be at least 8 characters';
    if (password !== confirmPassword) return 'Passwords do not match';
    return null;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const validationError = validateForm();
    if (validationError) {
      setError(validationError);
      return;
    }

    setLoading(true);

    try {
      // Call backend API to reset password
      const response = await fetch(`${API_BASE_URL}/auth/reset-password`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          token: resetToken,
          password,
        }),
      });

      if (response.ok) {
        setSuccess(true);
        setPassword('');
        setConfirmPassword('');
        
        // Redirect after showing success message
        setTimeout(() => {
          onResetComplete?.();
        }, 2000);
      } else {
        try {
          const data = await response.json();
          setError(data.detail || 'Failed to reset password. Your reset link may have expired.');
        } catch {
          setError(`Server error (${response.status}): ${response.statusText}`);
        }
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to reset password';
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

  if (!tokenValid) {
    return (
      <div className="login-page">
        <div className="login-container">
          <div className="login-branding">
            <div className="branding-content">
              <div className="logo-section">
                <div className="logo-icon">🏗️</div>
                <h1>SIMRAS</h1>
              </div>
              <p className="tagline">Smart Infrastructure Monitoring & Risk Assistance System</p>
            </div>
          </div>

          <div className="login-form-section">
            <div className="form-container">
              <h2>Reset Your Password</h2>
              
              <div className="error-alert">
                <span className="error-icon">⚠️</span>
                <span>Invalid or missing reset token. Please request a new password reset link.</span>
              </div>

              <div className="form-footer">
                <button 
                  type="button"
                  onClick={() => window.location.href = '/auth/login'}
                  className="forgot-password-link"
                >
                  Back to login
                </button>
              </div>
            </div>
          </div>
        </div>

        <footer className="login-footer">
          <p>&copy; 2026 SIMRAS. Government of Andhra Pradesh.</p>
        </footer>
      </div>
    );
  }

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

        {/* Right side - Reset password form */}
        <div className="login-form-section">
          <div className="form-container">
            <h2>Create New Password</h2>
            <p className="form-subtitle">Enter your new password below</p>

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
                  <p className="font-bold">Password reset successfully!</p>
                  <p className="text-sm">Your password has been updated. Redirecting to login...</p>
                </div>
              </div>
            )}

            {!success && (
              <form onSubmit={handleSubmit}>
                <div className="form-group">
                  <label htmlFor="password">New Password (min 8 characters) *</label>
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

                <div className="form-group">
                  <label htmlFor="confirmPassword">Confirm Password *</label>
                  <input
                    id="confirmPassword"
                    type="password"
                    placeholder="••••••••"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    disabled={loading}
                    required
                  />
                </div>

                <p className="form-hint">
                  Use a strong password with uppercase, lowercase, numbers, and special characters.
                </p>

                <button 
                  type="submit" 
                  className="sign-in-button"
                  disabled={loading}
                >
                  {loading ? 'Resetting...' : 'Reset Password'}
                </button>
              </form>
            )}

            <div className="form-footer">
              <button 
                type="button"
                onClick={() => window.location.href = '/auth/login'}
                className="forgot-password-link"
              >
                Back to login
              </button>
            </div>

            <div className="demo-notice">
              <p className="notice-title">Security Note</p>
              <p className="notice-text">
                This link will expire in 1 hour for security purposes.
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
