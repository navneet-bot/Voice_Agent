'use client';
import { useState, useEffect } from 'react';
import DashboardLayout from '@/components/DashboardLayout';

export default function LogsPage() {
  const [campaigns, setCampaigns] = useState([]);
  const [selectedCampaign, setSelectedCampaign] = useState('');
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);

  const API = process.env.NEXT_PUBLIC_API_URL || `http://${typeof window !== 'undefined' ? window.location.hostname : 'localhost'}:8000`;

  useEffect(() => {
    fetch(`${API}/api/campaigns`)
      .then(r => r.ok ? r.json() : [])
      .then(data => {
        setCampaigns(data);
        if (data.length > 0) {
          setSelectedCampaign(data[0].id);
        }
        setLoading(false);
      })
      .catch(e => {
        console.error(e);
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    if (!selectedCampaign) return;
    setLoading(true);
    fetch(`${API}/api/campaigns/${selectedCampaign}/results`)
      .then(r => r.ok ? r.json() : [])
      .then(data => {
        setLogs(data);
        setLoading(false);
      })
      .catch(e => {
        console.error(e);
        setLoading(false);
      });
  }, [selectedCampaign]);

  return (
    <DashboardLayout>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <div>
          <h2 className="h4 fw-bold mb-1">Call Logs & QA</h2>
          <p className="text-muted small mb-0">Review transcripts and audio recordings</p>
        </div>
        <button className="btn btn-outline-secondary btn-sm px-3 shadow-sm" disabled={logs.length === 0}>
          Export Logs
        </button>
      </div>
      
      <div className="card border-0 shadow-sm mb-4">
        <div className="card-body py-3 d-flex align-items-center gap-3">
          <label className="fw-bold small text-muted text-nowrap mb-0">Select Campaign:</label>
          <select 
            className="form-select form-select-sm w-auto" 
            value={selectedCampaign} 
            onChange={(e) => setSelectedCampaign(e.target.value)}
          >
            {campaigns.length === 0 && <option value="">No campaigns available</option>}
            {campaigns.map(c => (
              <option key={c.id} value={c.id}>{c.id}</option>
            ))}
          </select>
        </div>
      </div>

      {loading ? (
        <div className="text-center py-5"><span className="spinner-border text-primary"></span></div>
      ) : logs.length === 0 ? (
        <div className="card border-0 shadow-sm">
          <div className="card-body p-5 text-center text-muted">
            <div className="fs-1 mb-3">📞</div>
            <h6>No Call Logs Found</h6>
            <p className="small">Logs for the selected campaign will appear here once calls are completed.</p>
          </div>
        </div>
      ) : (
        <div className="card border-0 shadow-sm">
          <div className="table-responsive">
            <table className="table table-hover align-middle mb-0">
              <thead className="table-light text-muted small">
                <tr>
                  <th className="py-3 px-4">Lead Name</th>
                  <th className="py-3">Phone</th>
                  <th className="py-3">Outcome</th>
                  <th className="py-3">Interested</th>
                  <th className="py-3">Duration</th>
                  <th className="py-3 text-end px-4">Actions</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((log) => (
                  <tr key={log.id || log.lead_id}>
                    <td className="px-4 py-3 fw-medium">{log.lead_name || 'Unknown'}</td>
                    <td className="py-3">{log.phone || '—'}</td>
                    <td className="py-3">
                      <span className={`badge ${log.status === 'completed' ? 'bg-success' : 'bg-warning'}`}>
                        {log.outcome || log.status || 'unknown'}
                      </span>
                    </td>
                    <td className="py-3">
                      {log.interested === 'Yes' ? (
                        <span className="text-success fw-bold">✓ Yes</span>
                      ) : log.interested === 'No' ? (
                        <span className="text-danger">✗ No</span>
                      ) : (
                        <span className="text-muted">—</span>
                      )}
                    </td>
                    <td className="py-3 text-muted small">{log.duration || '—'}</td>
                    <td className="py-3 px-4 text-end">
                      <button className="btn btn-sm btn-light border shadow-sm">QA Review</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </DashboardLayout>
  );
}
