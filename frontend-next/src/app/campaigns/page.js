'use client';
import DashboardLayout from '@/components/DashboardLayout';

export default function CampaignsPage() {
  return (
    <DashboardLayout>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <div>
          <h2 className="h4 fw-bold mb-1">Campaigns</h2>
          <p className="text-muted small mb-0">Manage outbound voice campaigns</p>
        </div>
        <button className="btn btn-primary btn-sm px-3 shadow-sm">
          + New Campaign
        </button>
      </div>
      
      <div className="card border-0 shadow-sm">
        <div className="card-body p-5 text-center text-muted">
          <div className="fs-1 mb-3">🚀</div>
          <h6>No active campaigns</h6>
          <p className="small">Click 'New Campaign' to start dialing.</p>
        </div>
      </div>
    </DashboardLayout>
  );
}
