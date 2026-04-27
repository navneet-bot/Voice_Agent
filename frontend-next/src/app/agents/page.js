'use client';
import { useState, useEffect } from 'react';
import DashboardLayout from '@/components/DashboardLayout';
import { useAuth } from '@/context/AuthContext';

export default function AgentsPage() {
  const { user } = useAuth();
  const [agents, setAgents] = useState([]);
  const [showModal, setShowModal] = useState(false);
  const [loading, setLoading] = useState(true);
  
  const [formData, setFormData] = useState({
    name: '',
    voice: '11labs-06nek6zjTCD1vCbtc8bc',
    language: 'English',
    max_duration: 300,
    provider: 'twilio',
    script: 'Hello, I am calling about...',
    data_fields: 'interested, budget, location'
  });

  const API = process.env.NEXT_PUBLIC_API_URL || `http://${typeof window !== 'undefined' ? window.location.hostname : 'localhost'}:8000`;

  const fetchAgents = async () => {
    setLoading(true);
    try {
      // If authorization is needed, we could add token
      const res = await fetch(`${API}/api/agents`);
      if (res.ok) {
        const data = await res.json();
        setAgents(Array.isArray(data) ? data : []);
      }
    } catch (err) {
      console.error('Failed to fetch agents', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAgents();
  }, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    const payload = {
      ...formData,
      data_fields: formData.data_fields.split(',').map(s => s.trim()).filter(Boolean)
    };

    try {
      const res = await fetch(`${API}/api/agents`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        setShowModal(false);
        setFormData({ ...formData, name: '', script: '' }); // reset some fields
        fetchAgents();
      } else {
        alert("Failed to create agent");
      }
    } catch (e) {
      console.error(e);
      alert("Error connecting to backend");
    }
  };

  return (
    <DashboardLayout>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <div>
          <h2 className="h4 fw-bold mb-1">Voice Agents</h2>
          <p className="text-muted small mb-0">Configure AI agent personas and voices</p>
        </div>
        {user?.role === 'admin' && (
          <button className="btn btn-primary btn-sm px-3 shadow-sm" onClick={() => setShowModal(true)}>
            + Create Agent
          </button>
        )}
      </div>
      
      {loading ? (
        <div className="text-center py-5"><span className="spinner-border text-primary"></span></div>
      ) : agents.length === 0 ? (
        <div className="card border-0 shadow-sm">
          <div className="card-body p-5 text-center text-muted">
            <div className="fs-1 mb-3">🤖</div>
            <h6>No Agents Configured</h6>
            <p className="small">Click 'Create Agent' to build your first AI persona.</p>
          </div>
        </div>
      ) : (
        <div className="row g-4">
          {agents.map((agent, index) => (
            <div key={agent.id || index} className="col-md-4">
              <div className="card border-0 shadow-sm h-100">
                <div className="card-body">
                  <div className="d-flex justify-content-between align-items-start mb-3">
                    <h5 className="fw-bold mb-0">🤖 {agent.name || 'Unnamed Agent'}</h5>
                    <span className="badge bg-light text-dark border">{agent.language || 'English'}</span>
                  </div>
                  <p className="small text-muted mb-2"><strong>Voice:</strong> {agent.voice || 'Default'}</p>
                  <p className="small text-muted mb-3"><strong>Provider:</strong> {agent.provider || 'twilio'}</p>
                  
                  <div className="small text-muted">
                    <strong className="d-block mb-1">Extracted Fields:</strong>
                    <div className="d-flex flex-wrap gap-1">
                      {agent.data_fields?.map((field, i) => (
                        <span key={i} className="badge bg-secondary-subtle text-secondary border">{field}</span>
                      ))}
                    </div>
                  </div>
                <div className="card-footer bg-white border-top py-3">
                  <small className="text-muted">ID: {(agent.id || agent.agent_id || '').substring(0,8)}...</small>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modal for Creating Agent */}
      {showModal && (
        <div className="modal show d-block" tabIndex="-1" style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
          <div className="modal-dialog modal-lg modal-dialog-centered">
            <div className="modal-content border-0 shadow">
              <div className="modal-header border-bottom-0 pb-0">
                <h5 className="modal-title fw-bold">Create New Voice Agent</h5>
                <button type="button" className="btn-close shadow-none" onClick={() => setShowModal(false)}></button>
              </div>
              <div className="modal-body">
                <form onSubmit={handleCreate}>
                  <div className="row g-3 mb-3">
                    <div className="col-md-6">
                      <label className="form-label small fw-bold">Agent Name</label>
                      <input type="text" className="form-control" required value={formData.name} onChange={e => setFormData({...formData, name: e.target.value})} placeholder="e.g. Sales Rep Priya" />
                    </div>
                    <div className="col-md-6">
                      <label className="form-label small fw-bold">Voice ID / Provider mapping</label>
                      <select className="form-select" value={formData.voice} onChange={e => setFormData({...formData, voice: e.target.value})}>
                        <option value="11labs-06nek6zjTCD1vCbtc8bc">ElevenLabs - Priya (Female)</option>
                        <option value="11labs-default">ElevenLabs - Default</option>
                      </select>
                    </div>
                  </div>
                  
                  <div className="row g-3 mb-3">
                    <div className="col-md-4">
                      <label className="form-label small fw-bold">Language</label>
                      <input type="text" className="form-control" value={formData.language} onChange={e => setFormData({...formData, language: e.target.value})} />
                    </div>
                    <div className="col-md-4">
                      <label className="form-label small fw-bold">Provider</label>
                      <select className="form-select" value={formData.provider} onChange={e => setFormData({...formData, provider: e.target.value})}>
                        <option value="twilio">Twilio</option>
                        <option value="demo">Demo Web</option>
                      </select>
                    </div>
                    <div className="col-md-4">
                      <label className="form-label small fw-bold">Max Duration (sec)</label>
                      <input type="number" className="form-control" value={formData.max_duration} onChange={e => setFormData({...formData, max_duration: parseInt(e.target.value) || 300})} />
                    </div>
                  </div>

                  <div className="mb-3">
                    <label className="form-label small fw-bold">Data Extraction Fields (Comma separated)</label>
                    <input type="text" className="form-control" value={formData.data_fields} onChange={e => setFormData({...formData, data_fields: e.target.value})} placeholder="interested, budget, location" />
                  </div>

                  <div className="mb-4">
                    <label className="form-label small fw-bold">Agent Prompt / Script</label>
                    <textarea className="form-control" rows="5" required value={formData.script} onChange={e => setFormData({...formData, script: e.target.value})} placeholder="You are an AI assistant..."></textarea>
                  </div>

                  <div className="d-flex justify-content-end gap-2">
                    <button type="button" className="btn btn-light border" onClick={() => setShowModal(false)}>Cancel</button>
                    <button type="submit" className="btn btn-primary px-4">Create Agent</button>
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
