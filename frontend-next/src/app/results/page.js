'use client';
import { useEffect, useState } from 'react';
import DashboardLayout from '@/components/DashboardLayout';
import { useAuth } from '@/context/AuthContext';

export default function CallResults() {
  const { activeClient } = useAuth();
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(true);
  const isFinserv = activeClient === 'finserv';
  
  // We'll mimic fetching 'default' campaign results
  useEffect(() => {
    let active = true;
    
    // Function to ping server API for demo results matching index.html
    const fetchResults = async () => {
      try {
        const API = process.env.NEXT_PUBLIC_API_URL || '';
        const res = await fetch(`${API}/api/campaigns/default/results`);
        const json = await res.json();
        if (active) {
          setLeads(json);
          setLoading(false);
        }
      } catch (e) {
        console.error("Failed to load results", e);
        if (active) setLoading(false);
      }
    };

    fetchResults();
    // Poll every 5s instead of 3s to be lighter on server in React
    const int = setInterval(fetchResults, 5000);

    return () => {
      active = false;
      clearInterval(int);
    };
  }, [activeClient]);

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
                <th className="fw-semibold py-3">{isFinserv ? 'Objection' : 'Budget'}</th>
                <th className="fw-semibold py-3">Callback</th>
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
                  <td className="py-3 text-secondary">{l.budget || l.objection || '—'}</td>
                  <td className="py-3 text-secondary">{l.callback || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </DashboardLayout>
  );
}
