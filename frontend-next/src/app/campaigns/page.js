'use client';
import { useState, useEffect } from 'react';
import DashboardLayout from '@/components/DashboardLayout';
import { useAuth } from '@/context/AuthContext';

export default function CampaignsPage() {
  const { user } = useAuth();
  const [campaigns, setCampaigns] = useState([]);
  const [agents, setAgents] = useState([]);
  const [showModal, setShowModal] = useState(false);
  const [loading, setLoading] = useState(true);
  
  const [formData, setFormData] = useState({
    campaignId: '',
    agentId: '',
    telephonyProvider: 'demo',
    leadsCsv: 'John Doe,+1234567890\nJane Smith,+0987654321'
  });

  const API = process.env.NEXT_PUBLIC_API_URL || `http://${typeof window !== 'undefined' ? window.location.hostname : 'localhost'}:8000`;

  const fetchData = async () => {
    setLoading(true);
    try {
      const [cRes, aRes] = await Promise.all([
        fetch(`${API}/api/campaigns`),
        fetch(`${API}/api/agents`)
      ]);
      if (cRes.ok) setCampaigns(await cRes.json());
      if (aRes.ok) setAgents(await aRes.json());
    } catch (err) {
      console.error('Failed to fetch data', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!formData.campaignId || !formData.agentId) return alert("Campaign ID and Agent required");

    // Parse leads
    const leads = formData.leadsCsv.split('\n').map(line => {
      const [name, phone] = line.split(',');
      if (name && phone) return { name: name.trim(), phone: phone.trim() };
      return null;
    }).filter(Boolean);

    try {
      // 1. Upload Leads
      await fetch(`${API}/api/leads/upload`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ campaignId: formData.campaignId, leads })
      });

      // 2. Start Campaign
      const res = await fetch(`${API}/api/campaigns/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          campaignId: formData.campaignId,
          agentId: formData.agentId,
          telephonyProvider: formData.telephonyProvider
        })
      });

      if (res.ok) {
        setShowModal(false);
        setFormData({ ...formData, campaignId: '' });
        fetchData();
      } else {
        alert("Failed to start campaign");
      }
    } catch (err) {
      console.error(err);
      alert("Error starting campaign");
    }
  };

  return (
    <DashboardLayout>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <div>
          <h2 className="h4 fw-bold mb-1">Campaigns</h2>
          <p className="text-muted small mb-0">Manage outbound voice campaigns</p>
        </div>
        {user?.role === 'admin' && (
          <button className="btn btn-primary btn-sm px-3 shadow-sm" onClick={() => setShowModal(true)}>
            + New Campaign
          </button>
        )}
      </div>
      
      {loading ? (
        <div className="text-center py-5"><span className="spinner-border text-primary"></span></div>
      ) : campaigns.length === 0 ? (
        <div className="card border-0 shadow-sm">
          <div className="card-body p-5 text-center text-muted">
            <div className="fs-1 mb-3">🚀</div>
            <h6>No active campaigns</h6>
            <p className="small">Click 'New Campaign' to start dialing.</p>
          </div>
        </div>
      ) : (
        <div className="card border-0 shadow-sm">
          <div className="table-responsive">
            <table className="table table-hover align-middle mb-0">
              <thead className="table-light text-muted small">
                <tr>
                  <th className="py-3 px-4">Campaign ID</th>
                  <th className="py-3">Status</th>
                  <th className="py-3">Provider</th>
                  <th className="py-3">Agent</th>
                  <th className="py-3 text-end px-4">Created</th>
                </tr>
              </thead>
              <tbody>
                {campaigns.map((c) => (
                  <tr key={c.id}>
                    <td className="px-4 py-3 fw-medium">{c.id}</td>
                    <td className="py-3">
                      <span className={`badge ${c.status === 'Active' ? 'bg-success' : 'bg-secondary'}`}>{c.status || 'Pending'}</span>
                    </td>
                    <td className="py-3"><span className="badge bg-light text-dark border">{c.telephony_provider || 'demo'}</span></td>
                    <td className="py-3 text-muted">{c.agent_id}</td>
                    <td className="py-3 px-4 text-end text-muted small">{new Date(c.created_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Modal */}
      {showModal && (
        <div className="modal show d-block" tabIndex="-1" style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
          <div className="modal-dialog modal-dialog-centered">
            <div className="modal-content border-0 shadow">
              <div className="modal-header border-bottom-0 pb-0">
                <h5 className="modal-title fw-bold">Start New Campaign</h5>
                <button type="button" className="btn-close shadow-none" onClick={() => setShowModal(false)}></button>
              </div>
              <div className="modal-body">
                <form onSubmit={handleCreate}>
                  <div className="mb-3">
                    <label className="form-label small fw-bold">Campaign ID (No spaces)</label>
                    <input type="text" className="form-control" required value={formData.campaignId} onChange={e => setFormData({...formData, campaignId: e.target.value.replace(/\s+/g, '-')})} placeholder="e.g. spring-sale-2024" />
                  </div>
                  
                  <div className="row g-3 mb-3">
                    <div className="col-md-6">
                      <label className="form-label small fw-bold">Select Agent</label>
                      <select className="form-select" required value={formData.agentId} onChange={e => setFormData({...formData, agentId: e.target.value})}>
                        <option value="">-- Select Agent --</option>
                        {agents.map(a => <option key={a.agent_id} value={a.agent_id}>{a.name}</option>)}
                        <option value="default">Default Agent</option>
                      </select>
                    </div>
                    <div className="col-md-6">
                      <label className="form-label small fw-bold">Telephony Provider</label>
                      <select className="form-select" value={formData.telephonyProvider} onChange={e => setFormData({...formData, telephonyProvider: e.target.value})}>
                        <option value="twilio">Twilio</option>
                        <option value="demo">Demo Web</option>
                      </select>
                    </div>
                  </div>

                  <div className="mb-4">
                    <label className="form-label small fw-bold">Leads (Name, Phone Number) - 1 per line</label>
                    <textarea className="form-control" rows="4" required value={formData.leadsCsv} onChange={e => setFormData({...formData, leadsCsv: e.target.value})} placeholder="John Doe,+1234567890"></textarea>
                    <div className="form-text small">Ensure phone numbers include country code.</div>
                  </div>

                  <div className="d-flex justify-content-end gap-2">
                    <button type="button" className="btn btn-light border" onClick={() => setShowModal(false)}>Cancel</button>
                    <button type="submit" className="btn btn-primary px-4">Launch Campaign</button>
                  </div>
                </form>
              </div>
            </div>
          </div>
        </div>
      )}
    </DashboardLayout>
  );
}
