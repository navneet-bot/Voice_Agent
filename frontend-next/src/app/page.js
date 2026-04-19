'use client';
import { useAuth } from '../context/AuthContext';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

export default function Home() {
  const { currentRole, login } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (currentRole === 'admin') router.push('/monitor');
    if (currentRole === 'client') router.push('/client-dashboard');
  }, [currentRole, router]);

  const handleLogin = (role) => {
    login(role);
  };

  if (currentRole) return null;

  return (
    <div className="d-flex align-items-center justify-content-center vh-100 bg-light">
      <div className="card shadow-sm border-0" style={{ maxWidth: '400px', width: '100%', borderRadius: '12px' }}>
        <div className="card-body p-5 text-center">
          <div className="mb-4">
            <h3 className="fw-bold mb-1">Cosmic <span className="text-primary">Chameleon</span></h3>
            <p className="text-muted small">Voice Agent Platform v2.0</p>
          </div>
          
          <h6 className="text-secondary mb-4 text-uppercase fw-semibold" style={{ letterSpacing: '1px' }}>Select Login Role</h6>
          
          <div className="d-grid gap-3">
            <button 
              className="btn btn-primary py-3 fw-semibold rounded-3 shadow-sm"
              onClick={() => handleLogin('admin')}
            >
              Sign In as Platform Admin
            </button>
            <button 
              className="btn btn-outline-secondary py-3 fw-semibold rounded-3"
              onClick={() => handleLogin('client')}
            >
              Sign In as Client User
            </button>
          </div>
          
          <div className="mt-4 pt-3 border-top text-muted small">
            Secure connection established.
          </div>
        </div>
      </div>
    </div>
  );
}
