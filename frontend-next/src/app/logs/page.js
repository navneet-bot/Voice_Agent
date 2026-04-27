'use client';
import DashboardLayout from '@/components/DashboardLayout';

export default function LogsPage() {
  return (
    <DashboardLayout>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <div>
          <h2 className="h4 fw-bold mb-1">Call Logs & QA</h2>
          <p className="text-muted small mb-0">Review transcripts and audio recordings</p>
        </div>
        <button className="btn btn-outline-secondary btn-sm px-3 shadow-sm">
          Export Logs
        </button>
      </div>
      
      <div className="card border-0 shadow-sm">
        <div className="card-body p-5 text-center text-muted">
          <div className="fs-1 mb-3">📞</div>
          <h6>Quality Assurance Center</h6>
          <p className="small">Recent call logs and extracted insights will populate here.</p>
        </div>
      </div>
    </DashboardLayout>
  );
}
