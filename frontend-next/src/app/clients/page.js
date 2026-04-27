'use client';
import DashboardLayout from '@/components/DashboardLayout';

export default function ClientsPage() {
  return (
    <DashboardLayout>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <div>
          <h2 className="h4 fw-bold mb-1">Clients</h2>
          <p className="text-muted small mb-0">Manage customer accounts and access</p>
        </div>
        <button className="btn btn-primary btn-sm px-3 shadow-sm">
          + Add Client
        </button>
      </div>
      
      <div className="card border-0 shadow-sm">
        <div className="card-body p-5 text-center text-muted">
          <div className="fs-1 mb-3">🏢</div>
          <h6>Client Directory</h6>
          <p className="small">Manage your enterprise client list and permissions.</p>
        </div>
      </div>
    </DashboardLayout>
  );
}
