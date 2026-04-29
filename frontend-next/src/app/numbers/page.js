'use client';
import { useEffect, useState } from 'react';
import DashboardLayout from '@/components/DashboardLayout';
import { useAuth } from '@/context/AuthContext';

export default function MyNumbers() {
  const { activeClient } = useAuth();
  const [numbers, setNumbers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchProvider, setSearchProvider] = useState('twilio');
  const [searchCountry, setSearchCountry] = useState('IN');
  const [searchResults, setSearchResults] = useState(null);
  const [searching, setSearching] = useState(false);

  useEffect(() => {
    let active = true;
    const fetchNumbers = async () => {
      setLoading(true);
      try {
        const API = process.env.NEXT_PUBLIC_API_URL || '';
        const res = await fetch(`${API}/api/telephony/numbers?client_id=${encodeURIComponent(activeClient)}`);
        if (active) {
          setNumbers(Array.isArray(json) ? json : []);
          setLoading(false);
        }
      } catch (e) {
        if (active) setLoading(false);
      }
    };
    fetchNumbers();
    return () => { active = false; };
  }, [activeClient]);

  const handleSearch = async () => {
    setSearching(true);
    try {
      const API = process.env.NEXT_PUBLIC_API_URL || '';
      const res = await fetch(`${API}/api/telephony/numbers/search?provider=${searchProvider}&country_code=${searchCountry}`, { method: 'POST' });
      const json = await res.json();
      setSearchResults(Array.isArray(json) ? json : []);
    } catch (e) {
      setSearchResults([]);
    }
    setSearching(false);
  };

  return (
    <DashboardLayout>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <div>
          <h2 className="h4 fw-bold mb-1">☎ My Phone Numbers</h2>
          <p className="text-muted small mb-0">Purchase numbers for outbound campaigns — assigned directly to your account.</p>
        </div>
      </div>

      <div className="card border-0 shadow-sm mb-4">
        <div className="card-header bg-white border-bottom py-3">
          <h6 className="mb-0 fw-bold">Search & Buy a Number</h6>
        </div>
        <div className="card-body p-4 d-flex align-items-end gap-3 flex-wrap">
          <div style={{ minWidth: '200px' }}>
            <label className="form-label small fw-semibold text-muted">Provider</label>
            <select className="form-select shadow-none" value={searchProvider} onChange={(e) => setSearchProvider(e.target.value)}>
              <option value="twilio">Twilio ($0.03/min)</option>
              <option value="plivo">Plivo ($0.02/min)</option>
              <option value="vapi">Vapi ($0.05/min)</option>
              <option value="demo">Demo Mode (Free)</option>
            </select>
          </div>
          <div>
            <label className="form-label small fw-semibold text-muted">Country</label>
            <select className="form-select shadow-none" value={searchCountry} onChange={(e) => setSearchCountry(e.target.value)}>
              <option value="IN">🇮🇳 India</option>
              <option value="US">🇺🇸 United States</option>
              <option value="GB">🇬🇧 United Kingdom</option>
            </select>
          </div>
          <button className="btn btn-primary px-4 shadow-sm" onClick={handleSearch} disabled={searching}>
            {searching ? 'Searching...' : 'Search Numbers'}
          </button>
        </div>
      </div>

      {searchResults !== null && (
        <div className="card border-0 shadow-sm mb-4">
          <div className="card-header bg-white border-bottom py-3">
            <h6 className="mb-0 fw-bold">Available Numbers</h6>
          </div>
          <div className="card-body p-0">
            {searchResults.length === 0 ? (
              <div className="p-4 text-muted text-center small">No numbers found.</div>
            ) : (
              <div className="table-responsive">
                <table className="table table-hover align-middle mb-0">
                  <thead className="table-light text-muted small">
                    <tr>
                      <th className="px-4 py-3">Number</th>
                      <th className="py-3">Region</th>
                      <th className="py-3">Capabilities</th>
                      <th className="py-3 text-end px-4">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {searchResults.map((n, i) => (
                      <tr key={i}>
                        <td className="px-4 py-3 fw-bold">{n.phone_number}</td>
                        <td className="py-3 text-muted">{n.locality || '—'}, {n.region || '—'}</td>
                        <td className="py-3">
                          <span className="badge bg-light text-dark shadow-sm border">{n.capabilities?.voice ? 'Voice' : ''}</span>
                        </td>
                        <td className="py-3 px-4 text-end">
                          <button className="btn btn-sm btn-outline-primary">Buy</button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      <div className="card border-0 shadow-sm">
        <div className="card-header bg-white border-bottom py-3">
          <h6 className="mb-0 fw-bold">My Numbers</h6>
        </div>
        <div className="card-body p-0">
          {loading ? (
            <div className="p-4 text-center text-muted small">Loading...</div>
          ) : numbers.length === 0 ? (
            <div className="p-5 text-center text-muted small">No numbers yet — search and buy one above.</div>
          ) : (
            <div className="table-responsive">
              <table className="table table-hover align-middle mb-0">
                <thead className="table-light text-muted small">
                  <tr>
                    <th className="px-4 py-3">Number</th>
                    <th className="py-3">Region</th>
                    <th className="py-3">Provider</th>
                    <th className="py-3">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {numbers.map((n, i) => (
                    <tr key={i}>
                      <td className="px-4 py-3 fw-bold">{n.phone}</td>
                      <td className="py-3 text-muted">{n.region || '—'}</td>
                      <td className="py-3">
                        <span className="badge bg-primary-subtle text-primary border border-primary-subtle rounded-pill">{n.provider}</span>
                      </td>
                      <td className="py-3">
                        <span className="badge bg-success-subtle text-success border border-success-subtle rounded-pill">Active</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

    </DashboardLayout>
  );
}
