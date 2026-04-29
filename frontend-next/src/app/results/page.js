'use client';
import { useEffect, useState } from 'react';
import DashboardLayout from '@/components/DashboardLayout';
import { useAuth } from '@/context/AuthContext';

export default function CallResults() {
  const { activeClient } = useAuth();
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // Transcripts lazy loading state
  const [expandedRow, setExpandedRow] = useState(null);
  const [transcriptsCache, setTranscriptsCache] = useState({});
  const [loadingTranscript, setLoadingTranscript] = useState(false);

  const isFinserv = activeClient === 'finserv';
  const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  
  useEffect(() => {
    let active = true;
    
    const fetchResults = async () => {
      try {
        // Here we default to 'default' campaign, but in a real app this might be dynamic
        const res = await fetch(`${API}/api/campaigns/default/results`);
        const json = await res.json();
        if (active) {
          setLeads(Array.isArray(json) ? json : []);
          setLoading(false);
        }
      } catch (e) {
        console.error("Failed to load results", e);
        if (active) setLoading(false);
      }
    };

    fetchResults();
    const int = setInterval(fetchResults, 5000);

    return () => {
      active = false;
      clearInterval(int);
    };
  }, [activeClient, API]);

  const toggleTranscript = async (leadId) => {
    if (expandedRow === leadId) {
      setExpandedRow(null);
      return;
    }
    
    setExpandedRow(leadId);
    
    // Lazy load if not in cache
    if (!transcriptsCache[leadId]) {
      setLoadingTranscript(true);
      try {
        const res = await fetch(`${API}/api/results/${leadId}/transcript`);
        const data = await res.json();
        setTranscriptsCache(prev => ({ ...prev, [leadId]: data }));
      } catch (e) {
        console.error("Failed to load transcript", e);
      } finally {
        setLoadingTranscript(false);
      }
    }
  };

  const processed = leads.filter(l => l.processed);
  const connected = processed.filter(l => l.status === 'Connected');

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

      <div className="row g-3 mb-4">
        <div className="col-md-4">
          <div className="card border-0 shadow-sm">
            <div className="card-body">
              <h6 className="text-muted small text-uppercase fw-semibold mb-1">Total Contacts</h6>
              <h3 className="mb-0 fw-bold">{leads.length}</h3>
            </div>
          </div>
        </div>
        <div className="col-md-4">
          <div className="card border-0 shadow-sm">
            <div className="card-body">
              <h6 className="text-muted small text-uppercase fw-semibold mb-1">Called</h6>
              <h3 className="mb-0 fw-bold">{processed.length}</h3>
              <div className="text-primary small mt-1 fw-bold">{leads.length > 0 ? Math.round((processed.length / leads.length) * 100) : 0}% done</div>
            </div>
          </div>
        </div>
        <div className="col-md-4">
          <div className="card border-0 shadow-sm">
            <div className="card-body">
              <h6 className="text-muted small text-uppercase fw-semibold mb-1">Connected</h6>
              <h3 className="mb-0 fw-bold">{connected.length}</h3>
              <div className="text-muted small mt-1">{processed.length > 0 ? Math.round((connected.length / processed.length) * 100) : 0}% connect rate</div>
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
                <th className="fw-semibold py-3">Recording & QA</th>
              </tr>
            </thead>
            <tbody>
              {loading && leads.length === 0 ? (
                <tr>
                  <td colSpan="7" className="text-center py-5 text-muted">
                    <div className="spinner-border spinner-border-sm me-2" role="status"></div>
                    Fetching live results...
                  </td>
                </tr>
              ) : leads.length === 0 ? (
                <tr>
                  <td colSpan="7" className="text-center py-5 text-muted">
                    No leads found for this campaign. Click start campaign first.
                  </td>
                </tr>
              ) : leads.map((l, i) => (
                <tr key={i}>
                  <td className="px-4 py-3 fw-medium text-dark">{l.name}</td>
                  <td className="py-3 text-secondary">{l.phone}</td>
                  <td className="py-3 text-muted small">{l.calledAt || '—'}</td>
                  <td className="py-3 text-secondary">{l.duration || '—'}</td>
                  <td className="py-3">
                    <span className={`badge ${l.status === 'Connected' ? 'bg-success-subtle text-success border border-success-subtle' : l.status === 'No Answer' ? 'bg-warning-subtle text-warning border border-warning-subtle' : 'bg-light text-secondary border'}`}>
                      {l.status}
                    </span>
                  </td>
                  <td className="py-3 fw-medium text-dark">{l.interested || '—'}</td>
                  <td className="py-3">
                    <div className="d-flex align-items-center gap-2">
                      {l.has_recording ? (
                        <audio 
                          src={`${API}${l.recording_url}`} 
                          controls 
                          preload="metadata" 
                          style={{ height: '32px', width: '200px' }} 
                        />
                      ) : (
                        <span className="text-muted small fst-italic">No Media</span>
                      )}
                      
                      <button 
                        className={`btn btn-sm ${expandedRow === (l.lead_id || l.id) ? 'btn-secondary' : 'btn-outline-secondary'}`}
                        onClick={() => toggleTranscript(l.lead_id || l.id)}
                        disabled={!l.has_transcript}
                      >
                        📄 {expandedRow === (l.lead_id || l.id) ? 'Hide' : 'Transcript'}
                      </button>
                    </div>
                  </td>
                </tr>
              )).reduce((acc, tr, i) => {
                // We map over leads and for each row we check if we need to append an expanded row
                const l = leads[i];
                const leadId = l.lead_id || l.id;
                acc.push(tr);
                
                if (expandedRow === leadId) {
                  const transcript = transcriptsCache[leadId] || [];
                  acc.push(
                    <tr key={`exp-${leadId}`} className="bg-light">
                      <td colSpan="7" className="p-0 border-bottom-0">
                        <div className="p-4 border-start border-4 border-secondary m-3 bg-white rounded shadow-sm">
                          <h6 className="fw-bold mb-3 d-flex align-items-center gap-2">
                            <span>💬 Conversation Transcript</span>
                            {loadingTranscript && !transcriptsCache[leadId] && (
                              <div className="spinner-border spinner-border-sm text-secondary" role="status"></div>
                            )}
                          </h6>
                          
                          <div className="transcript-chat" style={{ maxHeight: '300px', overflowY: 'auto' }}>
                            {transcript.length === 0 && !loadingTranscript ? (
                              <div className="text-muted small italic">No conversation data available.</div>
                            ) : (
                              <div className="d-flex flex-column gap-2 pe-2">
                                {transcript.map((msg, idx) => (
                                  <div key={idx} className={`d-flex ${msg.speaker === 'user' ? 'justify-content-end' : 'justify-content-start'}`}>
                                    <div 
                                      className={`px-3 py-2 rounded-3 ${msg.speaker === 'user' ? 'bg-primary text-white' : 'bg-light border'}`}
                                      style={{ maxWidth: '75%', fontSize: '0.9rem' }}
                                    >
                                      <div className={`small fw-bold mb-1 ${msg.speaker === 'user' ? 'text-white-50' : 'text-secondary'}`} style={{ fontSize: '0.7rem' }}>
                                        {msg.speaker === 'user' ? (l.name || 'User') : 'AI Agent'}
                                      </div>
                                      <div>{msg.text || msg.content}</div>
                                    </div>
                                  </div>
                                ))}
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
