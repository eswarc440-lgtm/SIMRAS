import { useState } from 'react';
import './LoginPage.css';

interface SignupPageProps {
  onSignupComplete?: () => void;
  onBackToLogin?: () => void;
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

export function SignupPage({ onSignupComplete, onBackToLogin }: SignupPageProps) {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    officer_id: '',
    phone: '',
    designation: '',
    password: '',
    confirmPassword: '',
  });

  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const validateForm = () => {
    if (!formData.name.trim()) return 'Full name is required';
    if (!formData.email.trim()) return 'Email is required';
    if (!formData.email.includes('@')) return 'Invalid email address';
    if (!formData.officer_id.trim()) return 'Officer ID is required';
    if (!formData.phone.trim()) return 'Phone number is required';
    if (!formData.designation.trim()) return 'Designation is required';
    if (formData.password.length < 8) return 'Password must be at least 8 characters';
    if (formData.password !== formData.confirmPassword) return 'Passwords do not match';
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
      // Call backend API to create account
      const response = await fetch(`${API_BASE_URL}/auth/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: formData.name,
          email: formData.email,
          officer_id: formData.officer_id,
          phone: formData.phone,
          designation: formData.designation,
          password: formData.password,
        }),
      });

      if (response.ok) {
        setSuccess(true);
        setFormData({
          name: '',
          email: '',
          officer_id: '',
          phone: '',
          designation: '',
          password: '',
          confirmPassword: '',
        });
        
        // Show success message for 2 seconds then redirect
        setTimeout(() => {
          onSignupComplete?.();
        }, 2000);
      } else {
        try {
          const data = await response.json();
          setError(data.detail || 'Account creation failed. Please try again.');
        } catch {
          setError(`Server error (${response.status}): ${response.statusText}`);
        }
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to create account';
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

        {/* Right side - Signup form */}
        <div className="login-form-section">
          <div className="form-container">
            <h2>Create Account</h2>
            <p className="form-subtitle">Register as a new officer</p>

            {error && (
              <div className="error-alert">
                <span className="error-icon">⚠️</span>
                <span>{error}</span>
              </div>
            )}

            {success && (
              <div className="success-alert">
                <span className="success-icon">✓</span>
                <span>Account created successfully! Redirecting to login...</span>
              </div>
            )}

            {!success && (
              <form onSubmit={handleSubmit}>
                <div className="form-group">
                  <label htmlFor="name">Full Name *</label>
                  <input
                    id="name"
                    name="name"
                    type="text"
                    placeholder="Your full name"
                    value={formData.name}
                    onChange={handleChange}
                    disabled={loading}
                    required
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="email">Email *</label>
                  <input
                    id="email"
                    name="email"
                    type="email"
                    placeholder="your.email@example.com"
                    value={formData.email}
                    onChange={handleChange}
                    disabled={loading}
                    required
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="officer_id">Officer ID *</label>
                  <input
                    id="officer_id"
                    name="officer_id"
                    type="text"
                    placeholder="e.g., AP_OFFICER_001"
                    value={formData.officer_id}
                    onChange={handleChange}
                    disabled={loading}
                    required
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="phone">Phone Number *</label>
                  <input
                    id="phone"
                    name="phone"
                    type="tel"
                    placeholder="10-digit mobile number"
                    value={formData.phone}
                    onChange={handleChange}
                    disabled={loading}
                    required
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="designation">Designation *</label>
                  <select
                    id="designation"
                    name="designation"
                    value={formData.designation}
                    onChange={handleChange}
                    disabled={loading}
                    required
                  >
                    <option value="">Select your designation</option>
                    <option value="Inspector">Inspector</option>
                    <option value="Senior Inspector">Senior Inspector</option>
                    <option value="Chief Inspector">Chief Inspector</option>
                    <option value="Reviewer">Reviewer</option>
                    <option value="Coordinator">Coordinator</option>
                    <option value="Admin">Admin</option>
                  </select>
                </div>

                <div className="form-group">
                  <label htmlFor="password">Password (min 8 characters) *</label>
                  <input
                    id="password"
                    name="password"
                    type="password"
                    placeholder="••••••••"
                    value={formData.password}
                    onChange={handleChange}
                    disabled={loading}
                    required
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="confirmPassword">Confirm Password *</label>
                  <input
                    id="confirmPassword"
                    name="confirmPassword"
                    type="password"
                    placeholder="••••••••"
                    value={formData.confirmPassword}
                    onChange={handleChange}
                    disabled={loading}
                    required
                  />
                </div>

                <button 
                  type="submit" 
                  className="sign-in-button"
                  disabled={loading}
                >
                  {loading ? 'Creating Account...' : 'Create Account'}
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
              <p className="notice-title">Account Creation</p>
              <p className="notice-text">
                Your account will be reviewed by an administrator before activation.
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
