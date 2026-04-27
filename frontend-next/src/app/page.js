'use client';
import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '../context/AuthContext';
import { auth } from '../lib/firebase';
import {
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signInWithPopup,
  GoogleAuthProvider,
  sendPasswordResetEmail,
} from 'firebase/auth';

const googleProvider = new GoogleAuthProvider();

export default function LoginPage() {
  const { currentRole, loading } = useAuth();
  const router = useRouter();

  const [mode, setMode] = useState('login'); // 'login' | 'signup' | 'reset'
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [info, setInfo] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [showPass, setShowPass] = useState(false);

  // Redirect if already logged in
  useEffect(() => {
    if (!loading && currentRole === 'admin') router.push('/monitor');
    if (!loading && currentRole === 'client') router.push('/client-dashboard');
  }, [currentRole, loading, router]);

  if (loading || currentRole) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', background: '#080c18' }}>
      <div className="cc-spinner" />
    </div>
  );

  const clearMessages = () => { setError(''); setInfo(''); };

  // ── Email / Password handlers ────────────────────────────────────────────
  const handleEmailAuth = async (e) => {
    e.preventDefault();
    clearMessages();
    if (mode === 'signup' && password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }
    setSubmitting(true);
    try {
      if (mode === 'login') {
        await signInWithEmailAndPassword(auth, email, password);
      } else {
        await createUserWithEmailAndPassword(auth, email, password);
      }
      // onAuthStateChanged in AuthContext handles redirect
    } catch (err) {
      setError(friendlyError(err.code));
    } finally {
      setSubmitting(false);
    }
  };

  const handleReset = async (e) => {
    e.preventDefault();
    clearMessages();
    if (!email) { setError('Enter your email address first.'); return; }
    setSubmitting(true);
    try {
      await sendPasswordResetEmail(auth, email);
      setInfo('Reset link sent! Check your inbox.');
      setMode('login');
    } catch (err) {
      setError(friendlyError(err.code));
    } finally {
      setSubmitting(false);
    }
  };

  // ── Google Sign-in ───────────────────────────────────────────────────────
  const handleGoogle = async () => {
    clearMessages();
    setSubmitting(true);
    try {
      await signInWithPopup(auth, googleProvider);
      // Account is auto-created if it doesn't exist
    } catch (err) {
      if (err.code !== 'auth/popup-closed-by-user') {
        setError(friendlyError(err.code));
      }
    } finally {
      setSubmitting(false);
    }
  };

  // ── Error messages ───────────────────────────────────────────────────────
  function friendlyError(code) {
    const map = {
      'auth/user-not-found':        'No account found with this email.',
      'auth/wrong-password':        'Incorrect password. Try again.',
      'auth/email-already-in-use':  'An account with this email already exists.',
      'auth/weak-password':         'Password must be at least 6 characters.',
      'auth/invalid-email':         'Please enter a valid email address.',
      'auth/too-many-requests':     'Too many attempts. Please try again later.',
      'auth/network-request-failed':'Network error. Check your connection.',
      'auth/invalid-credential':    'Invalid email or password.',
    };
    return map[code] || 'Something went wrong. Please try again.';
  }

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        .cc-login-root {
          min-height: 100vh;
          background: #080c18;
          display: flex;
          align-items: center;
          justify-content: center;
          font-family: 'Inter', system-ui, sans-serif;
          position: relative;
          overflow: hidden;
          padding: 24px;
        }

        /* animated mesh gradient background */
        .cc-login-root::before {
          content: '';
          position: absolute;
          inset: 0;
          background:
            radial-gradient(ellipse 80% 60% at 20% 10%, rgba(99,102,241,0.18) 0%, transparent 60%),
            radial-gradient(ellipse 70% 70% at 80% 90%, rgba(124,58,237,0.15) 0%, transparent 60%),
            radial-gradient(ellipse 50% 50% at 50% 50%, rgba(16,185,129,0.05) 0%, transparent 70%);
          pointer-events: none;
        }

        /* floating orbs */
        .cc-orb {
          position: absolute;
          border-radius: 50%;
          filter: blur(80px);
          opacity: 0.25;
          animation: orb-float 8s ease-in-out infinite;
          pointer-events: none;
        }
        .cc-orb-1 { width: 400px; height: 400px; top: -100px; left: -100px; background: #6366f1; animation-delay: 0s; }
        .cc-orb-2 { width: 300px; height: 300px; bottom: -60px; right: -60px; background: #7c3aed; animation-delay: -4s; }
        @keyframes orb-float {
          0%, 100% { transform: translateY(0px) scale(1); }
          50%       { transform: translateY(-30px) scale(1.05); }
        }

        .cc-card {
          position: relative;
          z-index: 1;
          width: 100%;
          max-width: 420px;
          background: rgba(255,255,255,0.04);
          border: 1px solid rgba(255,255,255,0.1);
          border-radius: 20px;
          padding: 40px 36px;
          backdrop-filter: blur(20px);
          -webkit-backdrop-filter: blur(20px);
          box-shadow: 0 32px 80px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.08);
          animation: card-in 0.45s cubic-bezier(.16,1,.3,1) forwards;
        }
        @keyframes card-in {
          from { opacity: 0; transform: translateY(28px) scale(0.97); }
          to   { opacity: 1; transform: translateY(0) scale(1); }
        }

        /* logo */
        .cc-logo { text-align: center; margin-bottom: 28px; }
        .cc-logo-icon {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          width: 56px; height: 56px;
          border-radius: 16px;
          background: linear-gradient(135deg, #6366f1, #7c3aed);
          font-size: 26px;
          margin-bottom: 14px;
          box-shadow: 0 8px 32px rgba(99,102,241,0.4);
        }
        .cc-brand { font-size: 22px; font-weight: 700; color: #fff; letter-spacing: -0.3px; }
        .cc-brand span { color: #818cf8; }
        .cc-tagline { font-size: 12px; color: rgba(255,255,255,0.4); margin-top: 4px; letter-spacing: 0.5px; text-transform: uppercase; }

        /* mode tabs */
        .cc-tabs { display: flex; background: rgba(255,255,255,0.06); border-radius: 10px; padding: 3px; margin-bottom: 24px; }
        .cc-tab {
          flex: 1; padding: 8px; text-align: center; font-size: 13px; font-weight: 600;
          color: rgba(255,255,255,0.4); border-radius: 8px; cursor: pointer; transition: all 0.2s;
          user-select: none; border: none; background: none;
        }
        .cc-tab.active { background: rgba(99,102,241,0.3); color: #fff; }

        /* form */
        .cc-label { display: block; font-size: 12px; font-weight: 600; color: rgba(255,255,255,0.5); margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.5px; }
        .cc-input-wrap { position: relative; margin-bottom: 14px; }
        .cc-input {
          width: 100%; padding: 12px 14px; border-radius: 10px;
          background: rgba(255,255,255,0.07); border: 1px solid rgba(255,255,255,0.1);
          color: #fff; font-size: 14px; font-family: inherit; outline: none; transition: border 0.2s, background 0.2s;
          box-sizing: border-box;
        }
        .cc-input::placeholder { color: rgba(255,255,255,0.25); }
        .cc-input:focus { border-color: rgba(99,102,241,0.7); background: rgba(99,102,241,0.08); }
        .cc-input-icon { position: absolute; right: 12px; top: 50%; transform: translateY(-50%); cursor: pointer; color: rgba(255,255,255,0.3); font-size: 16px; user-select: none; }
        .cc-input-icon:hover { color: rgba(255,255,255,0.6); }

        /* buttons */
        .cc-btn {
          width: 100%; padding: 13px; border-radius: 10px; font-size: 14px; font-weight: 600;
          font-family: inherit; cursor: pointer; transition: all 0.2s; border: none; display: flex; align-items: center; justify-content: center; gap: 8px;
        }
        .cc-btn-primary {
          background: linear-gradient(135deg, #6366f1, #7c3aed);
          color: #fff; box-shadow: 0 4px 20px rgba(99,102,241,0.35);
        }
        .cc-btn-primary:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 6px 28px rgba(99,102,241,0.5); }
        .cc-btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }

        .cc-btn-google {
          background: rgba(255,255,255,0.07); color: #fff;
          border: 1px solid rgba(255,255,255,0.15);
          margin-bottom: 0;
        }
        .cc-btn-google:hover:not(:disabled) { background: rgba(255,255,255,0.12); }
        .cc-btn-google:disabled { opacity: 0.5; cursor: not-allowed; }

        /* divider */
        .cc-divider { display: flex; align-items: center; gap: 12px; margin: 18px 0; }
        .cc-divider-line { flex: 1; height: 1px; background: rgba(255,255,255,0.1); }
        .cc-divider-text { font-size: 12px; color: rgba(255,255,255,0.3); font-weight: 500; }

        /* alerts */
        .cc-error { background: rgba(239,68,68,0.12); border: 1px solid rgba(239,68,68,0.3); border-radius: 8px; padding: 10px 12px; color: #fca5a5; font-size: 13px; margin-bottom: 14px; }
        .cc-info  { background: rgba(16,185,129,0.1); border: 1px solid rgba(16,185,129,0.3); border-radius: 8px; padding: 10px 12px; color: #6ee7b7; font-size: 13px; margin-bottom: 14px; }

        /* forgot */
        .cc-forgot { text-align: right; margin-top: -8px; margin-bottom: 14px; }
        .cc-link { background: none; border: none; color: rgba(129,140,248,0.8); font-size: 12px; font-weight: 500; cursor: pointer; padding: 0; font-family: inherit; }
        .cc-link:hover { color: #818cf8; text-decoration: underline; }

        /* footer */
        .cc-footer { text-align: center; margin-top: 20px; font-size: 12px; color: rgba(255,255,255,0.25); }

        /* spinner */
        .cc-spinner {
          width: 20px; height: 20px;
          border: 2px solid rgba(255,255,255,0.3);
          border-top-color: #fff;
          border-radius: 50%;
          animation: cc-spin 0.7s linear infinite;
          display: inline-block;
        }
        @keyframes cc-spin { to { transform: rotate(360deg); } }

        /* Google icon SVG */
        .cc-google-icon { width: 18px; height: 18px; }
      `}</style>

      <div className="cc-login-root">
        <div className="cc-orb cc-orb-1" />
        <div className="cc-orb cc-orb-2" />

        <div className="cc-card">
          {/* Logo */}
          <div className="cc-logo">
            <div className="cc-logo-icon">🦎</div>
            <div className="cc-brand">Cosmic <span>Chameleon</span></div>
            <div className="cc-tagline">Voice Agent Platform v2.0</div>
          </div>

          {/* Mode tabs — only show for login/signup */}
          {mode !== 'reset' && (
            <div className="cc-tabs">
              <button className={`cc-tab ${mode === 'login' ? 'active' : ''}`} onClick={() => { setMode('login'); clearMessages(); }}>
                Sign In
              </button>
              <button className={`cc-tab ${mode === 'signup' ? 'active' : ''}`} onClick={() => { setMode('signup'); clearMessages(); }}>
                Sign Up
              </button>
            </div>
          )}

          {/* Reset mode heading */}
          {mode === 'reset' && (
            <div style={{ textAlign: 'center', marginBottom: '20px' }}>
              <div style={{ color: '#fff', fontWeight: 700, fontSize: '18px', marginBottom: '6px' }}>Reset Password</div>
              <div style={{ color: 'rgba(255,255,255,0.4)', fontSize: '13px' }}>We&apos;ll send a link to your email</div>
            </div>
          )}

          {/* Error / Info */}
          {error && <div className="cc-error">⚠️ {error}</div>}
          {info  && <div className="cc-info">✅ {info}</div>}

          {/* ── Form ── */}
          <form onSubmit={mode === 'reset' ? handleReset : handleEmailAuth} autoComplete="on">
            <label className="cc-label" htmlFor="cc-email">Email</label>
            <div className="cc-input-wrap">
              <input
                id="cc-email"
                type="email"
                className="cc-input"
                placeholder="you@company.com"
                value={email}
                onChange={e => setEmail(e.target.value)}
                required
                autoComplete="email"
              />
            </div>

            {mode !== 'reset' && (
              <>
                <label className="cc-label" htmlFor="cc-password">Password</label>
                <div className="cc-input-wrap">
                  <input
                    id="cc-password"
                    type={showPass ? 'text' : 'password'}
                    className="cc-input"
                    style={{ paddingRight: '40px' }}
                    placeholder={mode === 'signup' ? 'Min 6 characters' : '••••••••'}
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                    required
                    autoComplete={mode === 'signup' ? 'new-password' : 'current-password'}
                  />
                  <span className="cc-input-icon" onClick={() => setShowPass(p => !p)} title={showPass ? 'Hide' : 'Show'}>
                    {showPass ? '🙈' : '👁️'}
                  </span>
                </div>
              </>
            )}

            {mode === 'signup' && (
              <>
                <label className="cc-label" htmlFor="cc-confirm">Confirm Password</label>
                <div className="cc-input-wrap">
                  <input
                    id="cc-confirm"
                    type={showPass ? 'text' : 'password'}
                    className="cc-input"
                    placeholder="Re-enter password"
                    value={confirmPassword}
                    onChange={e => setConfirmPassword(e.target.value)}
                    required
                    autoComplete="new-password"
                  />
                </div>
              </>
            )}

            {mode === 'login' && (
              <div className="cc-forgot">
                <button type="button" className="cc-link" onClick={() => { setMode('reset'); clearMessages(); }}>
                  Forgot password?
                </button>
              </div>
            )}

            {mode === 'reset' && (
              <div className="cc-forgot">
                <button type="button" className="cc-link" onClick={() => { setMode('login'); clearMessages(); }}>
                  ← Back to Sign In
                </button>
              </div>
            )}

            <button type="submit" className="cc-btn cc-btn-primary" disabled={submitting} style={{ marginBottom: '0' }}>
              {submitting ? <span className="cc-spinner" /> : (
                mode === 'login'  ? 'Sign In' :
                mode === 'signup' ? 'Create Account' :
                'Send Reset Link'
              )}
            </button>
          </form>

          {/* ── Google ── (not shown on reset) */}
          {mode !== 'reset' && (
            <>
              <div className="cc-divider">
                <div className="cc-divider-line" />
                <div className="cc-divider-text">or continue with</div>
                <div className="cc-divider-line" />
              </div>

              <button type="button" className="cc-btn cc-btn-google" onClick={handleGoogle} disabled={submitting}>
                <svg className="cc-google-icon" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
                  <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                  <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
                  <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
                </svg>
                Continue with Google
              </button>
            </>
          )}

          <div className="cc-footer">
            Secured by Firebase Authentication
          </div>
        </div>
      </div>
    </>
  );
}
