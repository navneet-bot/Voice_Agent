'use client';
import { useEffect, useState } from 'react';
import DashboardLayout from '@/components/DashboardLayout';
import { useAuth } from '@/context/AuthContext';

export default function CallResults() {
  const { activeClient } = useAuth();
  const [campaigns, setCampaigns] = useState([]);
  const [selectedCampaign, setSelectedCampaign] = useState('');
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(true);

  // Transcripts lazy loading state
  const [expandedRow, setExpandedRow] = useState(null);
  const [transcriptsCache, setTranscriptsCache] = useState({});
  const [loadingTranscript, setLoadingTranscript] = useState(false);

  const isFinserv = activeClient === 'finserv';
  const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  // Step 1: Fetch all campaigns so user can pick one
  useEffect(() => {
    fetch(`${API}/api/campaigns`)
      .then(r => r.ok ? r.json() : [])
      .then(data => {
        const arr = Array.isArray(data) ? data : [];
        setCampaigns(arr);
        if (arr.length > 0) setSelectedCampaign(arr[0].id);
      })
      .catch(console.error);
  }, [API]);

  // Step 2: Poll results for the selected campaign every 5s
  useEffect(() => {
    if (!selectedCampaign) return;
    let active = true;

    const fetchResults = async () => {
      try {
        const res = await fetch(`${API}/api/campaigns/${selectedCampaign}/results`);
        const json = await res.json();
        if (active) {
          setLeads(Array.isArray(json) ? json : []);
          setLoading(false);
        }
      } catch (e) {
        console.error('Failed to load results', e);
        if (active) setLoading(false);
      }
    };

    setLoading(true);
    fetchResults();
    const int = setInterval(fetchResults, 5000);
    return () => { active = false; clearInterval(int); };
  }, [selectedCampaign, API]);

  const toggleTranscript = async (leadId) => {
    if (expandedRow === leadId) { setExpandedRow(null); return; }
    setExpandedRow(leadId);
    if (!transcriptsCache[leadId]) {
      setLoadingTranscript(true);
      try {
        const res = await fetch(`${API}/api/results/${leadId}/transcript`);
        const data = await res.json();
        setTranscriptsCache(prev => ({ ...prev, [leadId]: data }));
      } catch (e) {
        console.error('Failed to load transcript', e);
      } finally {
        setLoadingTranscript(false);
      }
    }
  };

  // Hot lead: interested=Yes AND has a scheduled callback/visit
  const isHotLead = (l) => {
    const interested = l.interested === 'Yes';
    const cb = (l.callback || '').toLowerCase();
    const hasCallback = cb && cb !== '—' && cb !== '';
    const ld = l.lead_data || {};
    const visitAgreed = ld.site_visit_agreed || ld.visit_confirmed ||
      cb.includes('sunday') || cb.includes('saturday') ||
      cb.includes('monday') || cb.includes('friday');
    return interested && (hasCallback || visitAgreed);
  };

  const processed = leads.filter(l => l.processed);
  const connected = processed.filter(l => l.status === 'Connected');
  const hotLeads = leads.filter(isHotLead);

  return (
    <DashboardLayout>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <div>
          <h2 className="h4 fw-bold mb-1">Call Results — {isFinserv ? 'Renewal Drive' : 'Live Campaign'}</h2>
          <p className="text-muted small mb-0">Live conversational data securely written to your structured storage.</p>
        </div>
        <button className="btn btn-outline-secondary btn-sm d-flex align-items-center gap-2">
          <span>↓</span> Export CSV
        </button>
      </div>

      {/* Campaign Selector */}
      <div className="card border-0 shadow-sm mb-4">
        <div className="card-body py-3 d-flex align-items-center gap-3">
          <label className="fw-bold small text-muted text-nowrap mb-0">Select Campaign:</label>
          <select
            className="form-select form-select-sm w-auto"
            value={selectedCampaign}
            onChange={(e) => { setSelectedCampaign(e.target.value); setLeads([]); }}
          >
            {campaigns.length === 0 && <option value="">No campaigns available</option>}
            {campaigns.map(c => (
              <option key={c.id} value={c.id}>{c.name || c.id} ({c.status})</option>
            ))}
          </select>
          {hotLeads.length > 0 && (
            <span className="badge rounded-pill" style={{ background: '#0f172a', color: '#f8fafc', fontSize: '12px' }}>
              🔥 {hotLeads.length} Hot Lead{hotLeads.length > 1 ? 's' : ''}
            </span>
          )}
        </div>
      </div>

      {/* Stats */}
      <div className="row g-3 mb-4">
        <div className="col-md-3">
          <div className="card border-0 shadow-sm">
            <div className="card-body">
              <h6 className="text-muted small text-uppercase fw-semibold mb-1">Total Contacts</h6>
              <h3 className="mb-0 fw-bold">{leads.length}</h3>
            </div>
          </div>
        </div>
        <div className="col-md-3">
          <div className="card border-0 shadow-sm">
            <div className="card-body">
              <h6 className="text-muted small text-uppercase fw-semibold mb-1">Called</h6>
              <h3 className="mb-0 fw-bold">{processed.length}</h3>
              <div className="text-primary small mt-1 fw-bold">
                {leads.length > 0 ? Math.round((processed.length / leads.length) * 100) : 0}% done
              </div>
            </div>
          </div>
        </div>
        <div className="col-md-3">
          <div className="card border-0 shadow-sm">
            <div className="card-body">
              <h6 className="text-muted small text-uppercase fw-semibold mb-1">Connected</h6>
              <h3 className="mb-0 fw-bold">{connected.length}</h3>
              <div className="text-muted small mt-1">
                {processed.length > 0 ? Math.round((connected.length / processed.length) * 100) : 0}% connect rate
              </div>
            </div>
          </div>
        </div>
        <div className="col-md-3">
          <div className="card border-0 shadow-sm" style={{ background: hotLeads.length > 0 ? '#0f172a' : undefined }}>
            <div className="card-body">
              <h6 className="small text-uppercase fw-semibold mb-1"
                style={{ color: hotLeads.length > 0 ? '#94a3b8' : undefined }}>
                🔥 Hot Leads
              </h6>
              <h3 className="mb-0 fw-bold" style={{ color: hotLeads.length > 0 ? '#f8fafc' : undefined }}>
                {hotLeads.length}
              </h3>
              <div className="small mt-1" style={{ color: hotLeads.length > 0 ? '#22c55e' : '#6b7280' }}>
                {hotLeads.length > 0 ? 'Agreed to visit / buy' : 'None yet'}
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="card border-0 shadow-sm">
        <div className="table-responsive">
          <table className="table table-hover align-middle mb-0 text-nowrap">
            <thead className="table-light text-muted small">
              <tr>
                <th className="fw-semibold px-4 py-3">Name</th>
                <th className="fw-semibold py-3">Phone</th>
                <th className="fw-semibold py-3">Called At</th>
                <th className="fw-semibold py-3">Duration</th>
                <th className="fw-semibold py-3">Status</th>
                <th className="fw-semibold py-3">{isFinserv ? 'Renewal Confirmed' : 'Interested'}</th>
                <th className="fw-semibold py-3">Callback / Visit</th>
                <th className="fw-semibold py-3">Recording &amp; QA</th>
              </tr>
            </thead>
            <tbody>
              {loading && leads.length === 0 ? (
                <tr>
                  <td colSpan="8" className="text-center py-5 text-muted">
                    <div className="spinner-border spinner-border-sm me-2" role="status"></div>
                    Fetching live results...
                  </td>
                </tr>
              ) : leads.length === 0 ? (
                <tr>
                  <td colSpan="8" className="text-center py-5 text-muted">
                    No results found for this campaign. Start the campaign first.
                  </td>
                </tr>
              ) : leads.map((l, i) => (
                <tr
                  key={i}
                  style={isHotLead(l) ? { background: '#0f172a', color: '#f8fafc' } : {}}
                >
                  <td className="px-4 py-3 fw-bold">
                    {isHotLead(l) && <span className="me-1">🔥</span>}
                    {l.name}
                  </td>
                  <td className="py-3" style={{ color: isHotLead(l) ? '#94a3b8' : '#6b7280' }}>{l.phone}</td>
                  <td className="py-3 small" style={{ color: isHotLead(l) ? '#94a3b8' : '#6b7280' }}>{l.calledAt || '—'}</td>
                  <td className="py-3" style={{ color: isHotLead(l) ? '#94a3b8' : '#6b7280' }}>{l.duration || '—'}</td>
                  <td className="py-3">
                    <span className={`badge ${
                      l.status === 'Connected'
                        ? isHotLead(l) ? 'bg-success text-white' : 'bg-success-subtle text-success border border-success-subtle'
                        : l.status === 'No Answer' ? 'bg-warning-subtle text-warning border border-warning-subtle'
                        : 'bg-light text-secondary border'
                    }`}>
                      {l.status}
                    </span>
                  </td>
                  <td className="py-3 fw-medium">
                    {l.interested === 'Yes' ? (
                      <span style={{ color: isHotLead(l) ? '#4ade80' : '#16a34a', fontWeight: 700 }}>✓ Yes</span>
                    ) : l.interested === 'No' ? (
                      <span style={{ color: isHotLead(l) ? '#f87171' : '#dc2626' }}>✗ No</span>
                    ) : (
                      <span style={{ color: '#94a3b8' }}>—</span>
                    )}
                  </td>
                  <td className="py-3 small" style={{ color: isHotLead(l) ? '#22d3ee' : '#6b7280' }}>
                    {l.callback && l.callback !== '—' ? l.callback : '—'}
                  </td>
                  <td className="py-3">
                    <div className="d-flex align-items-center gap-2">
                      {l.has_recording ? (
                        <audio
                          src={`${API}${l.recording_url}`}
                          controls
                          preload="metadata"
                          style={{ height: '32px', width: '180px' }}
                        />
                      ) : (
                        <span className="text-muted small fst-italic">No Media</span>
                      )}
                      <button
                        className={`btn btn-sm ${
                          expandedRow === (l.lead_id || l.id)
                            ? 'btn-secondary'
                            : isHotLead(l) ? 'btn-outline-light' : 'btn-outline-secondary'
                        }`}
                        onClick={() => toggleTranscript(l.lead_id || l.id)}
                        disabled={!l.has_transcript}
                      >
                        📄 {expandedRow === (l.lead_id || l.id) ? 'Hide' : 'Transcript'}
                      </button>
                    </div>
                  </td>
                </tr>
              )).reduce((acc, tr, i) => {
                const l = leads[i];
                const leadId = l.lead_id || l.id;
                acc.push(tr);
                if (expandedRow === leadId) {
                  const transcript = transcriptsCache[leadId] || [];
                  acc.push(
                    <tr key={`exp-${leadId}`} className="bg-light">
                      <td colSpan="8" className="p-0 border-bottom-0">
                        <div className="p-4 border-start border-4 border-secondary m-3 bg-white rounded shadow-sm">
                          <h6 className="fw-bold mb-3 d-flex align-items-center gap-2">
                            <span>💬 Conversation Transcript</span>
                            {loadingTranscript && !transcriptsCache[leadId] && (
                              <div className="spinner-border spinner-border-sm text-secondary" role="status"></div>
                            )}
                          </h6>
                          <div className="transcript-chat" style={{ maxHeight: '300px', overflowY: 'auto' }}>
                            {transcript.length === 0 && !loadingTranscript ? (
                              <div className="text-muted small fst-italic">No conversation data available.</div>
                            ) : (
                              <div className="d-flex flex-column gap-2 pe-2">
                                {transcript.map((msg, idx) => {
                                  const isUser = msg.speaker === 'user' || msg.role === 'user';
                                  return (
                                    <div key={idx} className={`d-flex ${isUser ? 'justify-content-end' : 'justify-content-start'}`}>
                                      <div
                                        className={`px-3 py-2 rounded-3 ${isUser ? 'bg-primary text-white' : 'bg-light border'}`}
                                        style={{ maxWidth: '75%', fontSize: '0.9rem' }}
                                      >
                                        <div className={`small fw-bold mb-1 ${isUser ? 'text-white-50' : 'text-secondary'}`}
                                          style={{ fontSize: '0.7rem' }}>
                                          {isUser ? (l.name || 'User') : 'AI Agent'}
                                        </div>
                                        <div>{msg.text || msg.content}</div>
                                      </div>
                                    </div>
                                  );
                                })}
                              </div>
                            )}
                          </div>
                        </div>
                      </td>
                    </tr>
                  );
                }
                return acc;
              }, [])}
            </tbody>
          </table>
        </div>
      </div>
    </DashboardLayout>
  );
}
