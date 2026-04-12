/**
 * LoginPage — Split-screen Google authentication.
 * Left: Branded panel with animated line chart SVG
 * Right: Google sign-in button
 */
import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { motion } from 'framer-motion';

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleGoogleLogin = async () => {
    setLoading(true);
    setError(null);
    try {
      await login();
      navigate('/chat');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      {/* ── Left Panel ── */}
      <div className="login-left">
        <div className="login-left-content">
          <div className="login-brand">
            <span className="fx-mono-large">FX</span>
            <span className="login-wordmark">Fintex</span>
          </div>

          {/* Animated line chart SVG */}
          <div className="login-chart-container">
            <svg viewBox="0 0 500 200" className="login-chart-svg">
              <defs>
                <linearGradient id="chartGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="var(--accent)" stopOpacity="0.3" />
                  <stop offset="100%" stopColor="var(--accent)" stopOpacity="0" />
                </linearGradient>
              </defs>
              <motion.path
                d="M0,150 C50,120 80,160 130,100 C180,40 200,90 250,70 C300,50 320,110 370,60 C420,10 450,80 500,40"
                fill="none"
                stroke="var(--accent)"
                strokeWidth="2.5"
                initial={{ pathLength: 0, opacity: 0 }}
                animate={{ pathLength: 1, opacity: 1 }}
                transition={{ duration: 2.5, ease: 'easeInOut' }}
              />
              <motion.path
                d="M0,150 C50,120 80,160 130,100 C180,40 200,90 250,70 C300,50 320,110 370,60 C420,10 450,80 500,40 L500,200 L0,200 Z"
                fill="url(#chartGradient)"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 2.5, delay: 0.5 }}
              />
            </svg>
          </div>

          <blockquote className="login-quote">
            "The best investment you can make is in your own financial knowledge."
          </blockquote>
        </div>
      </div>

      {/* ── Right Panel ── */}
      <motion.div
        className="login-right"
        initial={{ opacity: 0, x: 30 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
      >
        <div className="login-form-area">
          <div className="login-form-monogram">
            <span className="fx-mono">FX</span>
          </div>

          <h1 className="login-heading">Welcome to Fintex</h1>
          <p className="login-subtext">Sign in to start your financial research</p>

          <button
            className="google-sign-in-btn"
            onClick={handleGoogleLogin}
            disabled={loading}
          >
            <svg width="20" height="20" viewBox="0 0 48 48">
              <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z" />
              <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z" />
              <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z" />
              <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z" />
            </svg>
            <span>{loading ? 'Signing in...' : 'Continue with Google'}</span>
          </button>

          {error && <p className="login-error">{error}</p>}

          <p className="login-terms">
            By signing in, you agree to our{' '}
            <a href="#">Terms of Service</a> and <a href="#">Privacy Policy</a>
          </p>

          <Link to="/" className="login-back">← Back to Home</Link>
        </div>
      </motion.div>
    </div>
  );
}
