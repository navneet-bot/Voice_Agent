'use client';

import Link from 'next/link';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import DashboardLayout from '@/components/DashboardLayout';
import { useAuth, clientProfile } from '@/context/AuthContext';
import { getProviderLabel } from '@/lib/providerDisplay';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const CLIENT_WS_SCOPED_EVENTS_ENABLED = process.env.NEXT_PUBLIC_WS_SCOPED_EVENTS_ENABLED === 'true';

function campaignSlug(name) {
  const slug = String(name || '')
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 48);
  return `${slug || 'campaign'}-${Date.now()}`;
}

function cleanLeads(rows) {
  return rows
    .map((row) => ({
      name: String(row.name || '').trim(),
      phone: String(row.phone || '').trim(),
    }))
    .filter((row) => row.name && row.phone);
}

function uniqueLeads(rows) {
  const seen = new Set();
  const leads = [];
  cleanLeads(rows).forEach((lead) => {
    const key = lead.phone.replace(/\D/g, '') || lead.phone.toLowerCase();
    if (!key || seen.has(key)) return;
    seen.add(key);
    leads.push(lead);
  });
  return leads;
}

function parseCsvLine(line) {
  const cells = [];
  let current = '';
  let quoted = false;

  for (let index = 0; index < line.length; index += 1) {
    const char = line[index];
    const next = line[index + 1];
    if (char === '"' && quoted && next === '"') {
      current += '"';
      index += 1;
    } else if (char === '"') {
      quoted = !quoted;
    } else if (char === ',' && !quoted) {
      cells.push(current.trim());
      current = '';
    } else {
      current += char;
    }
  }
  cells.push(current.trim());
  return cells;
}

function normalizeCsvHeader(value) {
  return String(value || '').trim().toLowerCase().replace(/[\s_-]+/g, '');
}

function csvToLeads(text) {
  const rows = String(text || '')
    .replace(/^\uFEFF/, '')
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .map(parseCsvLine);

  if (!rows.length) return [];

  const headers = rows[0].map(normalizeCsvHeader);
  const nameIndex = headers.findIndex((header) => ['name', 'fullname', 'leadname', 'customername', 'contactname'].includes(header));
  const phoneIndex = headers.findIndex((header) => ['phone', 'phonenumber', 'mobile', 'mobilenumber', 'number', 'contactnumber'].includes(header));
  const hasHeader = phoneIndex >= 0;
  const dataRows = hasHeader ? rows.slice(1) : rows;
  const resolvedNameIndex = hasHeader && nameIndex >= 0 ? nameIndex : 0;
  const resolvedPhoneIndex = hasHeader ? phoneIndex : rows[0].length === 1 ? 0 : 1;

  return uniqueLeads(dataRows.map((row, index) => {
    const phone = String(row[resolvedPhoneIndex] || '').trim();
    const name = String(row[resolvedNameIndex] || '').trim() || `Lead ${index + 1}`;
    return { name, phone };
  }));
}

function dashboardWsUrl(clientId) {
  const base = API.replace(/^https/, 'wss').replace(/^http/, 'ws').replace(/\/$/, '');
  return `${base}/ws/dashboard?clientId=${encodeURIComponent(clientId)}`;
}

function liveEventLabel(eventType) {
  return String(eventType || '')
    .replace(/^call_/, '')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase()) || 'Update';
}

export default function ClientDashboard() {
  const { activeClient, currentRole, user, clientAssignment } = useAuth();
  const profile = currentRole === 'client' && user?.clientId
    ? { name: user.clientName || user.name, agent: user.agentName || 'Assigned Agent', agentId: user.agentId }
    : clientProfile[activeClient];
  const assignedAgent = clientAssignment?.assignment?.agent || clientAssignment?.agents?.[0] || null;
  const agentId = assignedAgent?.id || user?.agentId || profile?.agentId || 'default';
  const agentName = assignedAgent?.name || user?.agentName || profile?.agent || 'Assigned Agent';
  const assignedProvider = assignedAgent?.provider || 'demo';
  const clientId = user?.clientId || activeClient;

  const [showLaunchModal, setShowLaunchModal] = useState(false);
  const [loading, setLoading] = useState(false);
  const [notice, setNotice] = useState(null);
  const [form, setForm] = useState({
    campaignName: '',
    telephonyProvider: '',
  });
  const [leadRows, setLeadRows] = useState([
    { name: '', phone: '' },
    { name: '', phone: '' },
  ]);
  const [csvLeads, setCsvLeads] = useState([]);
  const [csvFileName, setCsvFileName] = useState('');
  const [csvError, setCsvError] = useState('');
  const [recentCampaigns, setRecentCampaigns] = useState([]);
  const [campaignsLoading, setCampaignsLoading] = useState(true);
  const [lastCampaignRefresh, setLastCampaignRefresh] = useState('');
  const [liveEvents, setLiveEvents] = useState([]);
  const [liveSocketStatus, setLiveSocketStatus] = useState('connecting');
  const liveSocketRef = useRef(null);

  const providerOptions = useMemo(() => {
    const slugs = ['demo'];
    if (assignedProvider && !slugs.includes(assignedProvider)) slugs.push(assignedProvider);
    return slugs;
  }, [assignedProvider]);

  const selectedProvider = form.telephonyProvider || assignedProvider || 'demo';
  const clientLiveEventsEnabled = CLIENT_WS_SCOPED_EVENTS_ENABLED && Boolean(clientId);

  const loadRecentCampaigns = useCallback(async ({ silent = false } = {}) => {
    if (!clientId) {
      setRecentCampaigns([]);
      setCampaignsLoading(false);
      return;
    }
    if (!silent) setCampaignsLoading(true);
    try {
      const res = await fetch(`${API}/api/campaigns?clientId=${encodeURIComponent(clientId)}`);
      const data = res.ok ? await res.json() : [];
      setRecentCampaigns(Array.isArray(data) ? data.slice(0, 8) : []);
      setLastCampaignRefresh(new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
    } catch (error) {
      console.error('Failed to load recent campaigns', error);
      setRecentCampaigns([]);
    } finally {
      if (!silent) setCampaignsLoading(false);
    }
  }, [clientId]);

  const shouldAutoRefreshCampaigns = useMemo(() => (
    recentCampaigns.some((campaign) => ['active', 'pending'].includes(String(campaign.status || '').toLowerCase()))
  ), [recentCampaigns]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadRecentCampaigns();
  }, [loadRecentCampaigns]);

  useEffect(() => {
    if (!shouldAutoRefreshCampaigns) return undefined;
    const interval = window.setInterval(() => {
      loadRecentCampaigns({ silent: true });
    }, 5000);
    return () => window.clearInterval(interval);
  }, [loadRecentCampaigns, shouldAutoRefreshCampaigns]);

  useEffect(() => {
    if (!clientLiveEventsEnabled) return undefined;
    const socket = new WebSocket(dashboardWsUrl(clientId));
    liveSocketRef.current = socket;

    socket.onopen = () => setLiveSocketStatus('connected');
    socket.onerror = () => setLiveSocketStatus('error');
    socket.onclose = () => setLiveSocketStatus('closed');
    socket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        if (!(String(message.type || '').startsWith('call_') || message.type === 'campaign_completed')) return;
        const key = [
          message.type,
          message.campaignId,
          message.leadId,
          message.status,
          message.snippet,
        ].join(':');
        setLiveEvents((current) => {
          if (current[0]?.key === key) return current;
          return [
            {
              key,
              type: message.type,
              label: liveEventLabel(message.type),
              campaignId: message.campaignId,
              leadName: message.leadName || 'Lead',
              status: message.status || '',
              snippet: message.snippet || message.message || '',
              provider: message.provider || selectedProvider,
              receivedAt: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
            },
            ...current,
          ].slice(0, 8);
        });
        if (message.type === 'call_completed' || message.type === 'campaign_completed') {
          loadRecentCampaigns({ silent: true });
        }
      } catch (error) {
        console.error('Client dashboard WS parse error', error);
      }
    };

    return () => {
      if (liveSocketRef.current === socket) liveSocketRef.current = null;
      if ([WebSocket.CONNECTING, WebSocket.OPEN].includes(socket.readyState)) socket.close();
    };
  }, [clientId, clientLiveEventsEnabled, loadRecentCampaigns, selectedProvider]);

  const updateLead = (index, key, value) => {
    setLeadRows((rows) => rows.map((row, i) => (i === index ? { ...row, [key]: value } : row)));
  };

  const addLeadRow = () => {
    setLeadRows((rows) => [...rows, { name: '', phone: '' }]);
  };

  const removeLeadRow = (index) => {
    setLeadRows((rows) => (rows.length <= 1 ? rows : rows.filter((_, i) => i !== index)));
  };

  const resetLaunchForm = () => {
    setForm({ campaignName: '', telephonyProvider: '' });
    setLeadRows([{ name: '', phone: '' }, { name: '', phone: '' }]);
    setCsvLeads([]);
    setCsvFileName('');
    setCsvError('');
  };

  const handleCsvUpload = async (event) => {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;
    setCsvError('');
    try {
      const text = await file.text();
      const parsed = csvToLeads(text);
      if (!parsed.length) {
        setCsvLeads([]);
        setCsvFileName('');
        setCsvError('No valid leads found in the CSV.');
        return;
      }
      setCsvLeads(parsed);
      setCsvFileName(file.name);
    } catch (error) {
      setCsvLeads([]);
      setCsvFileName('');
      setCsvError('Could not read this CSV file.');
    }
  };

  const clearCsv = () => {
    setCsvLeads([]);
    setCsvFileName('');
    setCsvError('');
  };

  const launchCampaign = async (event) => {
    event.preventDefault();
    const leads = uniqueLeads([...csvLeads, ...leadRows]);
    if (!form.campaignName.trim()) {
      setNotice({ type: 'danger', text: 'Please enter a campaign name.' });
      return;
    }
    if (!agentId) {
      setNotice({ type: 'danger', text: 'No agent is assigned to this account yet.' });
      return;
    }
    if (!leads.length) {
      setNotice({ type: 'danger', text: 'Add at least one lead with name and phone number.' });
      return;
    }

    const campaignId = campaignSlug(form.campaignName);
    const telephonyProvider = selectedProvider;
    setLoading(true);
    setNotice(null);

    try {
      const uploadRes = await fetch(`${API}/api/leads/upload`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          campaignId,
          campaignName: form.campaignName.trim(),
          agentId,
          telephonyProvider,
          clientId,
          leads,
        }),
      });
      const uploadBody = await uploadRes.json().catch(() => ({}));
      if (!uploadRes.ok) throw new Error(uploadBody.detail || 'Lead upload failed');

      const startRes = await fetch(`${API}/api/campaigns/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          campaignId,
          agentId,
          telephonyProvider,
          clientId,
        }),
      });
      const startBody = await startRes.json().catch(() => ({}));
      if (!startRes.ok) throw new Error(startBody.detail || 'Campaign launch failed');

      const acceptedCount = uploadBody.count || leads.length;
      const ignoredCount = (uploadBody.summary?.duplicates || 0) + (uploadBody.summary?.invalid || 0);
      setShowLaunchModal(false);
      resetLaunchForm();
      await loadRecentCampaigns();
      setNotice({
        type: 'success',
        text: `Campaign "${form.campaignName.trim()}" started with ${acceptedCount} lead${acceptedCount === 1 ? '' : 's'}${ignoredCount ? `, ${ignoredCount} skipped` : ''}.`,
      });
    } catch (error) {
      setNotice({ type: 'danger', text: error.message || 'Campaign launch failed.' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <DashboardLayout>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <div>
          <h2 className="h4 fw-bold mb-1">Campaign Dashboard</h2>
          <p className="text-muted small mb-0">Welcome back, {profile?.name || user?.name}</p>
        </div>
        <button
          className="btn btn-primary px-4 fw-semibold shadow-sm rounded-3"
          onClick={() => {
            setNotice(null);
            setShowLaunchModal(true);
          }}
          disabled={loading}
        >
          {loading ? 'Launching...' : 'Launch Campaign'}
        </button>
      </div>

      {notice && (
        <div className={`alert alert-${notice.type} py-2 small`} role="status">
          {notice.text}
        </div>
      )}

      <div className="row g-4 mb-4">
        <div className="col-md-8">
          <div className="card border-0 shadow-sm h-100">
            <div className="card-header bg-white border-bottom py-3">
              <h6 className="mb-0 fw-bold">Active Agent Configuration</h6>
            </div>
            <div className="card-body p-4 d-flex align-items-center gap-4">
              <div
                className="rounded-circle d-flex align-items-center justify-content-center text-white"
                style={{ width: '80px', height: '80px', background: 'radial-gradient(circle at 30% 30%, #2563eb, #1e3a8a)', fontSize: '32px' }}
              >
                AI
              </div>
              <div>
                <h5 className="fw-bold mb-1">{agentName}</h5>
                <p className="text-muted small mb-2">{getProviderLabel('telephony', assignedProvider)} calling workflow</p>
                <div className="d-flex gap-2 flex-wrap">
                  <span className="badge bg-light border text-dark">Data capture enabled</span>
                  <span className="badge bg-light border text-dark">Campaign-ready</span>
                  <span className="badge bg-light border text-dark">Agent ID: {agentId}</span>
                </div>
              </div>
            </div>
            <div className="card-footer bg-light border-0 py-3 text-muted small">
              Campaign launch uses your assigned agent and your account-scoped phone routing.
            </div>
          </div>
        </div>

        <div className="col-md-4">
          <div className="card border-0 shadow-sm h-100 bg-primary text-white">
            <div className="card-body p-4 d-flex flex-column justify-content-center">
              <h6 className="fw-semibold mb-1 opacity-75">Available Credits</h6>
              <h2 className="fw-bold mb-3">12,450 <span className="fs-6 fw-normal opacity-75">mins</span></h2>

              <h6 className="fw-semibold mb-1 mt-3 opacity-75">Active Provider</h6>
              <h3 className="fw-bold m-0">{getProviderLabel('telephony', assignedProvider)}</h3>
            </div>
          </div>
        </div>
      </div>

      <div className="card border-0 shadow-sm mb-4">
        <div className="card-header bg-white border-bottom py-3 d-flex justify-content-between align-items-center">
          <div>
            <h6 className="mb-0 fw-bold">Recent Campaigns</h6>
            <div className="small text-muted">
              Track launches, lead counts, and results for this account.
              {shouldAutoRefreshCampaigns && <span className="text-success fw-semibold ms-2">Auto-refresh on</span>}
              {lastCampaignRefresh && <span className="ms-2">Updated {lastCampaignRefresh}</span>}
            </div>
          </div>
          <button className="btn btn-sm btn-outline-secondary" type="button" onClick={loadRecentCampaigns} disabled={campaignsLoading}>
            {campaignsLoading ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>
        <div className="table-responsive">
          <table className="table table-hover align-middle mb-0">
            <thead className="table-light text-muted small">
              <tr>
                <th className="fw-semibold px-4 py-3">Campaign</th>
                <th className="fw-semibold py-3">Status</th>
                <th className="fw-semibold py-3">Leads</th>
                <th className="fw-semibold py-3">Results</th>
                <th className="fw-semibold py-3 text-end pe-4">Action</th>
              </tr>
            </thead>
            <tbody>
              {campaignsLoading && recentCampaigns.length === 0 ? (
                <tr>
                  <td colSpan="5" className="text-center py-4 text-muted">
                    <span className="spinner-border spinner-border-sm me-2" role="status"></span>
                    Loading campaigns...
                  </td>
                </tr>
              ) : recentCampaigns.length === 0 ? (
                <tr>
                  <td colSpan="5" className="text-center py-4 text-muted">
                    No campaigns launched yet.
                  </td>
                </tr>
              ) : recentCampaigns.map((campaign) => (
                <tr key={campaign.id}>
                  <td className="px-4 py-3">
                    <div className="fw-bold">{campaign.name || campaign.id}</div>
                    <div className="text-muted small">{campaign.id}</div>
                  </td>
                  <td className="py-3">
                    <span className={`badge ${
                      campaign.status === 'Active'
                        ? 'bg-success-subtle text-success border border-success-subtle'
                        : campaign.status === 'Done'
                          ? 'bg-primary-subtle text-primary border border-primary-subtle'
                          : 'bg-light text-secondary border'
                    }`}>
                      {campaign.status || 'Pending'}
                    </span>
                  </td>
                  <td className="py-3 fw-semibold">{campaign.lead_count ?? 0}</td>
                  <td className="py-3 fw-semibold">{campaign.result_count ?? 0}</td>
                  <td className="py-3 text-end pe-4">
                    <Link className="btn btn-sm btn-outline-primary" href={`/results?campaign=${encodeURIComponent(campaign.id)}`}>
                      View Results
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {clientLiveEventsEnabled && (
        <div className="card border-0 shadow-sm mb-4">
          <div className="card-header bg-white border-bottom py-3 d-flex justify-content-between align-items-center">
            <div>
              <h6 className="mb-0 fw-bold">Live Activity</h6>
              <div className="small text-muted">Latest tenant-scoped campaign events for this account.</div>
            </div>
            <span className={`badge ${
              liveSocketStatus === 'connected'
                ? 'bg-success-subtle text-success border border-success-subtle'
                : liveSocketStatus === 'error'
                  ? 'bg-danger-subtle text-danger border border-danger-subtle'
                  : 'bg-light text-secondary border'
            }`}>
              {liveSocketStatus}
            </span>
          </div>
          <div className="table-responsive">
            <table className="table table-hover align-middle mb-0">
              <thead className="table-light text-muted small">
                <tr>
                  <th className="fw-semibold px-4 py-3">Time</th>
                  <th className="fw-semibold py-3">Event</th>
                  <th className="fw-semibold py-3">Lead</th>
                  <th className="fw-semibold py-3">Status</th>
                  <th className="fw-semibold py-3">Provider</th>
                </tr>
              </thead>
              <tbody>
                {liveEvents.length === 0 ? (
                  <tr>
                    <td colSpan="5" className="text-center py-4 text-muted">
                      Waiting for live campaign events.
                    </td>
                  </tr>
                ) : liveEvents.map((event) => (
                  <tr key={event.key}>
                    <td className="px-4 py-3 small text-muted">{event.receivedAt}</td>
                    <td className="py-3 fw-semibold">{event.label}</td>
                    <td className="py-3">{event.leadName}</td>
                    <td className="py-3">
                      <span className="badge bg-light text-secondary border">{event.status || event.snippet || 'Update'}</span>
                    </td>
                    <td className="py-3">{getProviderLabel('telephony', event.provider || selectedProvider)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {showLaunchModal && (
        <div className="modal show d-block" tabIndex="-1" style={{ backgroundColor: 'rgba(15,23,42,0.45)' }}>
          <div className="modal-dialog modal-lg modal-dialog-centered">
            <div className="modal-content border-0 shadow">
              <div className="modal-header border-bottom">
                <div>
                  <h5 className="modal-title fw-bold">Launch Campaign</h5>
                  <div className="small text-muted">{agentName} will call the leads you add below.</div>
                </div>
                <button type="button" className="btn-close shadow-none" onClick={() => setShowLaunchModal(false)} />
              </div>
              <form onSubmit={launchCampaign}>
                <div className="modal-body">
                  <div className="row g-3 mb-3">
                    <div className="col-md-7">
                      <label className="form-label small fw-bold">Campaign Name</label>
                      <input
                        type="text"
                        className="form-control shadow-none"
                        value={form.campaignName}
                        onChange={(e) => setForm((current) => ({ ...current, campaignName: e.target.value }))}
                        placeholder="May site visit follow-up"
                        required
                      />
                    </div>
                    <div className="col-md-5">
                      <label className="form-label small fw-bold">Calling Mode</label>
                      <select
                        className="form-select shadow-none"
                        value={selectedProvider}
                        onChange={(e) => setForm((current) => ({ ...current, telephonyProvider: e.target.value }))}
                      >
                        {providerOptions.map((provider) => (
                          <option key={provider} value={provider}>
                            {provider === 'demo' ? 'Demo calling' : getProviderLabel('telephony', provider)}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div className="border rounded-3 overflow-hidden">
                    <div className="d-flex justify-content-between align-items-center px-3 py-2 bg-light border-bottom">
                      <span className="small fw-bold">Lead Details</span>
                      <div className="d-flex gap-2 align-items-center">
                        <label className="btn btn-sm btn-outline-secondary mb-0">
                          Upload CSV
                          <input type="file" accept=".csv,text/csv" hidden onChange={handleCsvUpload} />
                        </label>
                        <button type="button" className="btn btn-sm btn-outline-primary" onClick={addLeadRow}>
                          Add Lead
                        </button>
                      </div>
                    </div>
                    <div className="p-3">
                      {csvError && (
                        <div className="alert alert-danger py-2 small mb-3">{csvError}</div>
                      )}
                      {csvLeads.length > 0 && (
                        <div className="border rounded-3 mb-3 overflow-hidden">
                          <div className="d-flex justify-content-between align-items-center bg-success-subtle px-3 py-2 border-bottom">
                            <div>
                              <div className="small fw-bold text-success">{csvLeads.length} CSV leads loaded</div>
                              <div className="small text-muted">{csvFileName}</div>
                            </div>
                            <button type="button" className="btn btn-sm btn-outline-secondary" onClick={clearCsv}>
                              Clear CSV
                            </button>
                          </div>
                          <div className="table-responsive">
                            <table className="table table-sm mb-0">
                              <tbody>
                                {csvLeads.slice(0, 5).map((lead, index) => (
                                  <tr key={`${lead.phone}-${index}`}>
                                    <td className="px-3 text-muted small">{lead.name}</td>
                                    <td className="px-3 text-muted small">{lead.phone}</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </div>
                      )}
                      {leadRows.map((lead, index) => (
                        <div key={index} className="row g-2 align-items-center mb-2">
                          <div className="col-md-5">
                            <input
                              type="text"
                              className="form-control shadow-none"
                              value={lead.name}
                              onChange={(e) => updateLead(index, 'name', e.target.value)}
                              placeholder="Lead name"
                            />
                          </div>
                          <div className="col-md-5">
                            <input
                              type="tel"
                              className="form-control shadow-none"
                              value={lead.phone}
                              onChange={(e) => updateLead(index, 'phone', e.target.value)}
                              placeholder="+91XXXXXXXXXX"
                            />
                          </div>
                          <div className="col-md-2 text-end">
                            <button type="button" className="btn btn-sm btn-outline-secondary" onClick={() => removeLeadRow(index)}>
                              Remove
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
                <div className="modal-footer border-top">
                  <button type="button" className="btn btn-light border" onClick={() => setShowLaunchModal(false)} disabled={loading}>
                    Cancel
                  </button>
                  <button type="submit" className="btn btn-primary px-4" disabled={loading}>
                    {loading ? 'Launching...' : 'Start Calling'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </DashboardLayout>
  );
}
