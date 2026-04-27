'use client';
import DashboardLayout from '@/components/DashboardLayout';

export default function AgentsPage() {
  return (
    <DashboardLayout>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <div>
          <h2 className="h4 fw-bold mb-1">Voice Agents</h2>
          <p className="text-muted small mb-0">Configure AI agent personas and voices</p>
        </div>
        <button className="btn btn-primary btn-sm px-3 shadow-sm">
          + Create Agent
        </button>
      </div>
      
      <div className="card border-0 shadow-sm">
        <div className="card-body p-5 text-center text-muted">
          <div className="fs-1 mb-3">🤖</div>
          <h6>Agent Management Pipeline</h6>
          <p className="small">Your configured agents will appear here.</p>
        </div>
      </div>
    </DashboardLayout>
  );
}
