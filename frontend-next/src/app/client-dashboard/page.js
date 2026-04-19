'use client';
import DashboardLayout from '@/components/DashboardLayout';
import { useAuth, clientProfile } from '@/context/AuthContext';
import { useState } from 'react';

export default function ClientDashboard() {
  const { activeClient } = useAuth();
  const profile = clientProfile[activeClient];
  const [loading, setLoading] = useState(false);

  const startCampaign = async () => {
    setLoading(true);
    // Simulate campaign start logic
    setTimeout(() => setLoading(false), 2000);
  };

  return (
    <DashboardLayout>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <div>
          <h2 className="h4 fw-bold mb-1">Campaign Dashboard</h2>
          <p className="text-muted small mb-0">Welcome back, {profile?.name}</p>
        </div>
        <button 
          className="btn btn-primary px-4 fw-semibold shadow-sm rounded-3 d-flex align-items-center gap-2"
          onClick={startCampaign}
          disabled={loading}
        >
          {loading ? (
            <><span className="spinner-border spinner-border-sm"></span> Launching...</>
          ) : (
            <>▶ Launch Campaign</>
          )}
        </button>
      </div>

      <div className="row g-4 mb-4">
        <div className="col-md-8">
          <div className="card border-0 shadow-sm h-100">
            <div className="card-header bg-white border-bottom py-3">
              <h6 className="mb-0 fw-bold">Active Agent Configuration</h6>
            </div>
            <div className="card-body p-4 d-flex align-items-center gap-4">
              <div 
                className="rounded-circle d-flex align-items-center justify-content-center text-white"
                style={{ width: '80px', height: '80px', background: 'radial-gradient(circle at 30% 30%, #7c3aed, #4c1d95)', fontSize: '32px' }}
              >
                🤖
              </div>
              <div>
                <h5 className="fw-bold mb-1">{profile?.agent}</h5>
                <p className="text-muted small mb-2">Real Estate Specialized Workflow (Voice/SMS)</p>
                <div className="d-flex gap-2">
                  <span className="badge bg-light border text-dark">Data capture enabled</span>
                  <span className="badge bg-light border text-dark">Appointment scheduling</span>
                </div>
              </div>
            </div>
            <div className="card-footer bg-light border-0 py-3 text-muted small">
              To request changes to your agent script, voice, or data fields — contact your Cosmic Chameleon account manager.
            </div>
          </div>
        </div>

        <div className="col-md-4">
          <div className="card border-0 shadow-sm h-100 bg-primary text-white" style={{ background: 'linear-gradient(135deg, #6366f1, #4f46e5)' }}>
            <div className="card-body p-4 d-flex flex-column justify-content-center">
              <h6 className="fw-semibold mb-1 opacity-75">Available Credits</h6>
              <h2 className="fw-bold mb-3">12,450 <span className="fs-6 fw-normal opacity-75">mins</span></h2>
              
              <h6 className="fw-semibold mb-1 mt-3 opacity-75">Active Numbers</h6>
              <h3 className="fw-bold m-0 d-flex align-items-center gap-2">
                2 <span className="badge bg-white text-primary rounded-pill small" style={{ fontSize: '11px' }}>Manage</span>
              </h3>
            </div>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
