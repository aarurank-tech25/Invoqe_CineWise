import { useState, useEffect, useRef } from 'react';
import { useAuth, useToast } from './context';
import { apiLogin, apiRegister, apiForgotPassword, apiValidateResetToken, apiResetPassword, apiGoogleLogin } from './api';

// ─────────────────────────────────────────────────────────────────────────────
// Eye Icons for Password Visibility
// ─────────────────────────────────────────────────────────────────────────────
function EyeIcon({ show }) {
  if (show) {
    return (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
        <circle cx="12" cy="12" r="3" />
      </svg>
    );
  }
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
      <line x1="1" y1="1" x2="23" y2="23" />
    </svg>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Reusable CineWise Logo Component
// ─────────────────────────────────────────────────────────────────────────────
export function CineWiseLogo({ size = 'medium', showTagline = false, className = '' }) {
  const heights = {
    compact: 36,
    medium: 52,
    large: 84,
    hero: 110,
  };
  const h = heights[size] || 52;

  return (
    <div className={`cinewise-logo-wrap ${className}`} style={{ display: 'inline-flex', flexDirection: 'column', alignItems: 'center' }}>
      <img
        src="/cinewise-logo.png"
        alt="CineWise — AI-Powered Movie Discovery"
        className="cinewise-logo-img"
        style={{
          height: `${h}px`,
          width: 'auto',
          maxWidth: '100%',
          objectFit: 'contain',
          display: 'block',
          filter: 'drop-shadow(0 2px 8px rgba(0,0,0,0.4))',
        }}
      />
      {showTagline && (
        <span className="cinewise-logo-tagline" style={{ marginTop: 6, fontSize: '0.75rem', color: 'var(--brand-accent)', letterSpacing: '0.5px', textTransform: 'uppercase', fontWeight: 600 }}>
          AI-Powered Movie Discovery &amp; Recommendation Platform
        </span>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Left Side Cinematic Artwork & Branding Panel for Split-Screen
// ─────────────────────────────────────────────────────────────────────────────
function AuthSplitLeft({ quote, description }) {
  return (
    <div className="auth-split-left">
      <div className="auth-film-backdrop" aria-hidden="true" />
      <div className="auth-left-content">
        <div className="auth-logo-badge">
          <CineWiseLogo size="large" />
        </div>

        <div className="auth-tagline-pill">
          AI-POWERED MOVIE DISCOVERY
        </div>

        <h2 className="auth-hero-heading">{quote || 'Find your next favourite film.'}</h2>

        <p className="auth-hero-description">
          {description ||
            'Explore high-dimensional content-based recommendations evaluating plot, themes, genres, and cast across 10,000+ curated global and Indian cinema titles.'}
        </p>

        <div className="auth-feature-points">
          <div className="auth-feature-item">
            <span className="auth-feature-icon">✨</span>
            <div>
              <strong>Cosine Similarity Engine</strong>
              <p>TF-IDF high-dimensional semantic vector ranking</p>
            </div>
          </div>
          <div className="auth-feature-item">
            <span className="auth-feature-icon">🎬</span>
            <div>
              <strong>10,029 Curated Movies</strong>
              <p>Multi-language coverage: Tamil, Malayalam, Telugu, Kannada, Hindi &amp; English</p>
            </div>
          </div>
          <div className="auth-feature-item">
            <span className="auth-feature-icon">🔖</span>
            <div>
              <strong>Personalized Watchlist</strong>
              <p>Isolated collection synced to your secure profile</p>
            </div>
          </div>
        </div>

        <div className="auth-left-footer">
          <span>&copy; {new Date().getFullYear()} CineWise Platform</span>
          <span>·</span>
          <span>Privacy &amp; Security First</span>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// 1. LOGIN PAGE (Split-Screen)
// ─────────────────────────────────────────────────────────────────────────────

export function LoginPage({ onNavigate, onSuccess }) {
  const googleButtonRef = useRef(null);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(() => localStorage.getItem('cw_remember') === 'true');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const { login } = useAuth();
  const { addToast } = useToast();



  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    const cleanEmail = email.trim();
    if (!cleanEmail || !password) {
      setError('Please provide both your email address and password.');
      return;
    }

    // Proceed with normal login
    try {
      const res = await apiLogin({ email: cleanEmail, password });
      if (res.user) {
        login(res.user);
        onSuccess && onSuccess(res.user);
        addToast({ type: 'success', message: 'Login successful' });
      }
    } catch (err) {
      setError(err.message || 'Login failed');
    } finally {
      setLoading(false);
    }

  };

  // Handle Google Sign‑In response
  const handleGoogleResponse = async (response) => {
    const token = response?.credential;
    if (!token) return;
    setLoading(true);
    try {
      const res = await apiGoogleLogin({ token });
      if (res.user) {
        login(res.user);
        addToast({ type: 'success', message: 'Signed in with Google' });
        onSuccess && onSuccess(res.user);
        onNavigate('recommendations');
      }
    } catch (err) {
      setError(err.message || 'Google sign‑in failed');
    } finally {
      setLoading(false);
    }
  };

    // Initialize Google Sign‑In button with script‑load handling
  useEffect(() => {
    const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;
    if (!clientId) {
      console.warn('VITE_GOOGLE_CLIENT_ID not set');
      return;
    }
    // Helper to initialize the button once the Google script is ready
    const initGoogle = () => {
      if (window.google && window.google.accounts && window.google.accounts.id) {
        window.google.accounts.id.initialize({
          client_id: clientId,
          callback: handleGoogleResponse,
        });
        if (googleButtonRef.current) {
          window.google.accounts.id.renderButton(googleButtonRef.current, {
            theme: 'filled_black',
            size: 'large',
            text: 'continue_with',
          });
        }
      }
    };
    // If script already loaded, initialise immediately
    if (window.google && window.google.accounts && window.google.accounts.id) {
      initGoogle();
    } else {
      // Attach a listener for the script load event
      const script = document.querySelector('script[src="https://accounts.google.com/gsi/client"]');
      if (script) {
        script.addEventListener('load', initGoogle);
        // Cleanup listener on unmount
        return () => script.removeEventListener('load', initGoogle);
      } else {
        // Fallback: poll until window.google becomes available (max 5 attempts)
        let attempts = 0;
        const interval = setInterval(() => {
          attempts += 1;
          if (window.google && window.google.accounts && window.google.accounts.id) {
            clearInterval(interval);
            initGoogle();
          } else if (attempts >= 5) {
            clearInterval(interval);
            console.error('Google Identity Services script failed to load');
          }
        }, 500);
        return () => clearInterval(interval);
      }
    }
  }, []);


  return (
    <div className="auth-split-container">
      <AuthSplitLeft
        quote="Find your next favourite film."
        description="Sign in to access your personal watchlist, view AI match analytics, and explore 10,000+ hand-curated movies."
      />

      <div className="auth-split-right">
        <div className="auth-card-panel">
          <div className="auth-header-mobile">
            <CineWiseLogo size="medium" />
          </div>

          <div className="auth-form-header">
            <h1 className="auth-title">Sign In</h1>
            <p className="auth-subtitle">Enter your credentials to continue to CineWise</p>
          </div>

          {error && (
            <div className="alert alert-error" role="alert">
              <span className="alert-icon">⚠️</span>
              <div>{error}</div>
            </div>
          )}

          <form onSubmit={handleSubmit} noValidate>
            <div className="form-group">
              <label className="form-label" htmlFor="login-email">
                Email Address
              </label>
              <input
                id="login-email"
                className="form-input"
                type="email"
                autoComplete="email"
                placeholder="name@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>

            <div className="form-group">
              <div className="form-label-row">
                <label className="form-label" htmlFor="login-password">
                  Password
                </label>
                <button
                  type="button"
                  className="form-link-subtle"
                  onClick={() => onNavigate('forgot-password')}
                  id="link-forgot-password"
                >
                  Forgot password?
                </button>
              </div>
              <div className="password-input-wrap">
                <input
                  id="login-password"
                  className="form-input"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  placeholder="Enter your password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
                <button
                  type="button"
                  className="password-toggle-btn"
                  onClick={() => setShowPassword(!showPassword)}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                  title={showPassword ? 'Hide password' : 'Show password'}
                >
                  <EyeIcon show={showPassword} />
                </button>
              </div>
            </div>

            <div className="auth-row-options">
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                />
                <span>Remember me</span>
              </label>
            </div>

          <div className="google-divider">
            <hr />
            <span>OR</span>
            <hr />
          </div>
          <div ref={googleButtonRef} className="google-signin-container"></div>

          <button
                id="btn-login-submit"
                type="submit"
                className="btn-primary auth-submit-btn"
                disabled={loading}
              >
                {loading ? (
                  <>
                    <span className="spinner-inline" /> Signing in…
                  </>
                ) : (
                  'Sign In'
                )}
              </button>
          </form>

          <div className="auth-switch-row">
            <span>Don&apos;t have an account yet?</span>
            <button
              type="button"
              className="form-link-highlight"
              onClick={() => onNavigate('register')}
              id="link-go-to-register"
            >
              Create an Account
            </button>
          </div>

          <div className="auth-guest-row">
            <button
              type="button"
              className="auth-guest-btn"
              onClick={() => onNavigate('recommendations')}
            >
              ← Continue as guest
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// 2. REGISTRATION PAGE (Split-Screen)
// ─────────────────────────────────────────────────────────────────────────────
export function RegisterPage({ onNavigate, onSuccess }) {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  const { addToast } = useToast();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccessMsg('');

    const cleanName = name.trim();
    const cleanEmail = email.trim().toLowerCase();

    if (!cleanName || !cleanEmail || !password || !confirmPassword) {
      setError('Please fill in all required fields.');
      return;
    }

    if (!cleanEmail.includes('@') || !cleanEmail.includes('.')) {
      setError('Please enter a valid email address.');
      return;
    }

    if (password.length < 6) {
      setError('Password must be at least 6 characters in length.');
      return;
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match. Please re-enter.');
      return;
    }

    setLoading(true);
    try {
      const res = await apiRegister({ name: cleanName, email: cleanEmail, password });
      if (res.success) {
        setSuccessMsg('Account created successfully! You can now sign in.');
        addToast('Registration successful! Please sign in.', 'success');
        setTimeout(() => {
          onNavigate('login');
        }, 1200);
      }
    } catch (err) {
      setError(err.message || 'Registration failed. Email may already be in use.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-split-container">
      <AuthSplitLeft
        quote="Join the CineWise cinema experience."
        description="Create your free CineWise account to curate a personalized watchlist, unlock fine-tuned AI recommendations, and track streaming availability across Indian & global platforms."
      />

      <div className="auth-split-right">
        <div className="auth-card-panel">
          <div className="auth-header-mobile">
            <CineWiseLogo size="medium" />
          </div>

          <div className="auth-form-header">
            <h1 className="auth-title">Create Account</h1>
            <p className="auth-subtitle">Get started with your free personalized CineWise profile</p>
          </div>

          {error && (
            <div className="alert alert-error" role="alert">
              <span className="alert-icon">⚠️</span>
              <div>{error}</div>
            </div>
          )}

          {successMsg && (
            <div className="alert alert-success" role="alert">
              <span className="alert-icon">✓</span>
              <div>{successMsg}</div>
            </div>
          )}

          <form onSubmit={handleSubmit} noValidate>
            <div className="form-group">
              <label className="form-label" htmlFor="reg-name">
                Full Name
              </label>
              <input
                id="reg-name"
                className="form-input"
                type="text"
                autoComplete="name"
                placeholder="Alex Smith"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="reg-email">
                Email Address
              </label>
              <input
                id="reg-email"
                className="form-input"
                type="email"
                autoComplete="email"
                placeholder="name@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="reg-password">
                Password
              </label>
              <div className="password-input-wrap">
                <input
                  id="reg-password"
                  className="form-input"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="new-password"
                  placeholder="Minimum 6 characters"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
                <button
                  type="button"
                  className="password-toggle-btn"
                  onClick={() => setShowPassword(!showPassword)}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                  title={showPassword ? 'Hide password' : 'Show password'}
                >
                  <EyeIcon show={showPassword} />
                </button>
              </div>
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="reg-confirm-password">
                Confirm Password
              </label>
              <div className="password-input-wrap">
                <input
                  id="reg-confirm-password"
                  className="form-input"
                  type={showConfirmPassword ? 'text' : 'password'}
                  autoComplete="new-password"
                  placeholder="Re-enter password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                />
                <button
                  type="button"
                  className="password-toggle-btn"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  aria-label={showConfirmPassword ? 'Hide confirm password' : 'Show confirm password'}
                  title={showConfirmPassword ? 'Hide confirm password' : 'Show confirm password'}
                >
                  <EyeIcon show={showConfirmPassword} />
                </button>
              </div>
            </div>

            <button
              id="btn-register-submit"
              type="submit"
              className="btn-primary auth-submit-btn"
              disabled={loading}
            >
              {loading ? (
                <>
                  <span className="spinner-inline" /> Creating account…
                </>
              ) : (
                'Create Account'
              )}
            </button>
          </form>

          <div className="auth-switch-row">
            <span>Already have an account?</span>
            <button
              type="button"
              className="form-link-highlight"
              onClick={() => onNavigate('login')}
              id="link-go-to-login"
            >
              Sign In
            </button>
          </div>

          <div className="auth-guest-row">
            <button
              type="button"
              className="auth-guest-btn"
              onClick={() => onNavigate('recommendations')}
            >
              ← Back to Catalog
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// 3. FORGOT PASSWORD PAGE (Dedicated Recovery Screen)
// ─────────────────────────────────────────────────────────────────────────────
export function ForgotPasswordPage({ onNavigate, onDirectReset }) {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setResult(null);

    const cleanEmail = email.trim();
    if (!cleanEmail) {
      setError('Please enter your email address.');
      return;
    }

    if (!cleanEmail.includes('@') || !cleanEmail.includes('.')) {
      setError('Please enter a valid email address format.');
      return;
    }

    setLoading(true);
    try {
      const data = await apiForgotPassword({ email: cleanEmail });
      setResult(data);
    } catch (err) {
      setError(err.message || 'Unable to process reset request. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-centered-container">
      <div className="auth-centered-card">
        <div style={{ textAlign: 'center', marginBottom: 20 }}>
          <CineWiseLogo size="large" showTagline={false} />
        </div>

        <div className="auth-form-header" style={{ textAlign: 'center' }}>
          <h1 className="auth-title">Password Recovery</h1>
          <p className="auth-subtitle">
            Enter the email address registered with your account to receive a secure password reset link.
          </p>
        </div>

        {error && (
          <div className="alert alert-error" role="alert">
            <span className="alert-icon">⚠️</span>
            <div>{error}</div>
          </div>
        )}

        {result && (
          <div className="auth-recovery-success">
            <div className="alert alert-success" role="alert">
              <span className="alert-icon">✓</span>
              <div>
                <strong>Request Received</strong>
                <p style={{ marginTop: 4, fontSize: '0.86rem' }}>{result.message}</p>
              </div>
            </div>

            {/* Development-Only Testing Mode Banner (When SMTP is unconfigured) */}
            {result.dev_mode && result.dev_reset_url && (
              <div className="dev-test-mode-box">
                <div className="dev-test-badge">⚙️ DEVELOPMENT TEST MODE</div>
                <p className="dev-test-text">
                  SMTP email credentials are not configured in <code>.env</code>. You can test the password recovery flow immediately using the generated secure token:
                </p>
                <div style={{ marginTop: 10 }}>
                  <button
                    type="button"
                    className="btn-primary"
                    style={{ width: '100%', padding: '10px 16px', fontSize: '0.88rem' }}
                    onClick={() => {
                      // Extract token from dev_reset_url
                      const match = result.dev_reset_url.match(/token=([^&]+)/);
                      const tok = match ? match[1] : '';
                      if (onDirectReset) onDirectReset(tok);
                      else {
                        window.history.pushState({}, '', result.dev_reset_url);
                        window.location.reload();
                      }
                    }}
                    id="btn-dev-open-reset"
                  >
                    Open Password Reset Form →
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {!result && (
          <form onSubmit={handleSubmit} noValidate>
            <div className="form-group">
              <label className="form-label" htmlFor="forgot-email">
                Registered Email Address
              </label>
              <input
                id="forgot-email"
                className="form-input"
                type="email"
                autoComplete="email"
                placeholder="name@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>

            <button
              id="btn-forgot-submit"
              type="submit"
              className="btn-primary auth-submit-btn"
              disabled={loading}
            >
              {loading ? (
                <>
                  <span className="spinner-inline" /> Sending reset link…
                </>
              ) : (
                'Send Reset Link'
              )}
            </button>
          </form>
        )}

        <div className="auth-back-nav" style={{ textAlign: 'center', marginTop: 24 }}>
          <button
            type="button"
            className="form-link-subtle"
            onClick={() => onNavigate('login')}
            id="link-back-to-login"
          >
            ← Back to Sign In
          </button>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// 4. RESET PASSWORD PAGE (Dedicated Token Validation & New Password Screen)
// ─────────────────────────────────────────────────────────────────────────────
export function ResetPasswordPage({ token: propToken, onNavigate }) {
  // Support token from prop or from current window query params
  const [token, setToken] = useState(() => {
    if (propToken) return propToken;
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get('token') || '';
  });

  const [checking, setChecking] = useState(true);
  const [tokenValid, setTokenValid] = useState(false);
  const [tokenError, setTokenError] = useState('');
  const [userEmail, setUserEmail] = useState('');

  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState('');
  const [success, setSuccess] = useState(false);

  const { addToast } = useToast();

  // Validate token on mount
  useEffect(() => {
    if (!token) {
      setChecking(false);
      setTokenValid(false);
      setTokenError('No password reset token was provided. Please request a new link.');
      return;
    }

    setChecking(true);
    apiValidateResetToken(token)
      .then((data) => {
        if (data.valid) {
          setTokenValid(true);
          setUserEmail(data.email || '');
        } else {
          setTokenValid(false);
          setTokenError(data.message || 'This password reset link is invalid or has expired.');
        }
      })
      .catch((err) => {
        setTokenValid(false);
        setTokenError(err.message || 'Failed to validate reset link.');
      })
      .finally(() => {
        setChecking(false);
      });
  }, [token]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setFormError('');

    if (!password || !confirmPassword) {
      setFormError('Please enter and confirm your new password.');
      return;
    }

    if (password.length < 6) {
      setFormError('Password must be at least 6 characters in length.');
      return;
    }

    if (password !== confirmPassword) {
      setFormError('Passwords do not match. Please ensure both passwords match.');
      return;
    }

    setSubmitting(true);
    try {
      const res = await apiResetPassword({
        token,
        password,
        confirm_password: confirmPassword,
      });

      if (res.success) {
        setSuccess(true);
        addToast('Password successfully reset! Please sign in.', 'success');
      }
    } catch (err) {
      setFormError(err.message || 'Failed to reset password. The link may have expired.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="auth-centered-container">
      <div className="auth-centered-card">
        <div style={{ textAlign: 'center', marginBottom: 20 }}>
          <CineWiseLogo size="large" showTagline={false} />
        </div>

        {checking && (
          <div style={{ textAlign: 'center', padding: '36px 0' }}>
            <span className="spinner" style={{ width: 28, height: 28 }} />
            <p style={{ marginTop: 16, color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
              Verifying security reset token…
            </p>
          </div>
        )}

        {!checking && !tokenValid && (
          <div className="auth-token-invalid">
            <div className="alert alert-error" role="alert">
              <span className="alert-icon">⚠️</span>
              <div>
                <strong>Invalid or Expired Link</strong>
                <p style={{ marginTop: 4, fontSize: '0.86rem' }}>{tokenError}</p>
              </div>
            </div>

            <div style={{ marginTop: 24, textAlign: 'center' }}>
              <button
                type="button"
                className="btn-primary"
                onClick={() => onNavigate('forgot-password')}
                id="btn-request-new-link"
              >
                Request a New Reset Link
              </button>
            </div>

            <div style={{ marginTop: 16, textAlign: 'center' }}>
              <button
                type="button"
                className="form-link-subtle"
                onClick={() => onNavigate('login')}
              >
                ← Back to Sign In
              </button>
            </div>
          </div>
        )}

        {!checking && tokenValid && !success && (
          <div>
            <div className="auth-form-header" style={{ textAlign: 'center' }}>
              <h1 className="auth-title">Set New Password</h1>
              <p className="auth-subtitle">
                {userEmail ? (
                  <>Resetting password for: <strong>{userEmail}</strong></>
                ) : (
                  'Choose a strong new password for your account'
                )}
              </p>
            </div>

            {formError && (
              <div className="alert alert-error" role="alert">
                <span className="alert-icon">⚠️</span>
                <div>{formError}</div>
              </div>
            )}

            <form onSubmit={handleSubmit} noValidate>
              <div className="form-group">
                <label className="form-label" htmlFor="new-password">
                  New Password
                </label>
                <div className="password-input-wrap">
                  <input
                    id="new-password"
                    className="form-input"
                    type={showPassword ? 'text' : 'password'}
                    autoComplete="new-password"
                    placeholder="Minimum 6 characters"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                  />
                  <button
                    type="button"
                    className="password-toggle-btn"
                    onClick={() => setShowPassword(!showPassword)}
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                  >
                    <EyeIcon show={showPassword} />
                  </button>
                </div>
              </div>

              <div className="form-group">
                <label className="form-label" htmlFor="confirm-new-password">
                  Confirm New Password
                </label>
                <div className="password-input-wrap">
                  <input
                    id="confirm-new-password"
                    className="form-input"
                    type={showConfirmPassword ? 'text' : 'password'}
                    autoComplete="new-password"
                    placeholder="Re-enter new password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    required
                  />
                  <button
                    type="button"
                    className="password-toggle-btn"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    aria-label={showConfirmPassword ? 'Hide password' : 'Show password'}
                  >
                    <EyeIcon show={showConfirmPassword} />
                  </button>
                </div>
              </div>

              <button
                id="btn-reset-password-submit"
                type="submit"
                className="btn-primary auth-submit-btn"
                disabled={submitting}
              >
                {submitting ? (
                  <>
                    <span className="spinner-inline" /> Updating password…
                  </>
                ) : (
                  'Update Password'
                )}
              </button>
            </form>

            {/* OR Divider */}
            <div className="auth-or-divider">
              <span className="or-text">OR</span>
            </div>
            {/* Google Sign‑In Button */}
            <div ref={googleButtonRef} className="google-signin-button" />



            <div className="auth-back-nav" style={{ textAlign: 'center', marginTop: 20 }}>
              <button
                type="button"
                className="form-link-subtle"
                onClick={() => onNavigate('login')}
              >
                Cancel and return to Sign In
              </button>
            </div>
          </div>
        )}

        {!checking && success && (
          <div className="auth-reset-success-box" style={{ textAlign: 'center', padding: '10px 0' }}>
            <div style={{ fontSize: '3rem', marginBottom: 12 }}>🎉</div>
            <h2 style={{ fontSize: '1.4rem', fontWeight: 700, color: 'var(--text-primary)', marginBottom: 8 }}>
              Password Reset Complete!
            </h2>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', lineHeight: 1.6, marginBottom: 24 }}>
              Your password has been successfully updated. You can now securely sign in to your CineWise account using your new credentials.
            </p>
            <button
              id="btn-go-to-login-after-reset"
              type="button"
              className="btn-primary"
              style={{ width: '100%', padding: '12px', fontSize: '0.95rem' }}
              onClick={() => onNavigate('login')}
            >
              Sign In with New Password →
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
