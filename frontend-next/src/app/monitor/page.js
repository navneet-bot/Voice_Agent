'use client';
import { useEffect, useState, useRef } from 'react';
import DashboardLayout from '@/components/DashboardLayout';

export default function AdminMonitor() {
  const [metrics, setMetrics] = useState({
    totalCalls: 0,
    activeAgents: 0,
    connectRate: 0,
    sysLoad: 'Normal'
  });
  const [liveCalls, setLiveCalls] = useState({});
  const wsRef = useRef(null);

  useEffect(() => {
    // Connect to global dashboard WebSocket over configured API URL
    const API = process.env.NEXT_PUBLIC_API_URL || `http://localhost:8000`;
    const wsUrl = `${API.replace(/^https/, 'wss').replace(/^http/, 'ws').replace(/\/$/, '')}/ws/dashboard`;
    wsRef.current = new WebSocket(wsUrl);

    wsRef.current.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === 'dashboard_update') {
          // Full snapshot
          const callsMap = {};
          let activeCnt = 0;
          let connectedCnt = 0;

          msg.calls.forEach(call => {
            callsMap[call.lead_id] = call;
            if (['ringing', 'connected', 'talking'].includes(call.status)) activeCnt++;
            if (['connected', 'talking'].includes(call.status)) connectedCnt++;
          });

          setLiveCalls(callsMap);
          setMetrics({
            totalCalls: msg.calls.length,
            activeAgents: activeCnt,
            connectRate: msg.calls.length > 0 ? Math.round((connectedCnt / msg.calls.length) * 100) : 0,
            sysLoad: 'Normal'
          });
        } else if (msg.type?.startsWith('call_')) {
          // Delta update
          setLiveCalls(prev => {
            const up = { ...prev };
            if (!up[msg.leadId]) up[msg.leadId] = { lead_id: msg.leadId };
            
            up[msg.leadId].status = msg.type.replace('call_', '');
            up[msg.leadId].lead_name = msg.leadName || up[msg.leadId].lead_name;
            up[msg.leadId].provider = msg.provider || up[msg.leadId].provider;
            
            if (msg.type === 'call_talking') {
              up[msg.leadId].last_snippet = msg.snippet;
            }
            if (msg.type === 'call_completed') {
              up[msg.leadId].result = msg.result;
            }
            return up;
          });
        }
      } catch (e) {
        console.error("Dashboard WS parse error", e);
      }
    };

    return () => {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.close();
      }
    };
  }, []);

  const getStatusBadge = (status) => {
    switch (status) {
      case 'ringing': return <span className="badge bg-warning text-dark"><span className="spinner-grow spinner-grow-sm me-1" aria-hidden="true"></span>Ringing</span>;
      case 'connected': return <span className="badge bg-success">Connected</span>;
      case 'talking': return <span className="badge bg-primary"><span className="spinner-grow spinner-grow-sm me-1" aria-hidden="true"></span>Talking</span>;
      case 'completed': return <span className="badge bg-secondary">Completed</span>;
      default: return <span className="badge bg-light text-dark">{status}</span>;
    }
  };

  return (
    <DashboardLayout>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <div>
          <h2 className="h4 mb-1 fw-bold">Live Monitor</h2>
          <p className="text-muted small mb-0">Real-time system oversight and active call tracking</p>
        </div>
        <div className="d-flex gap-2">
          <span className="badge bg-success-subtle text-success border border-success-subtle d-flex align-items-center gap-1 px-3 py-2">
            <span className="spinner-grow spinner-grow-sm" style={{ width: '8px', height: '8px' }}></span>
            System Online
          </span>
        </div>
      </div>

      <div className="row g-3 mb-4">
        <div className="col-md-3">
          <div className="card border-0 shadow-sm">
            <div className="card-body">
              <h6 className="text-muted small text-uppercase fw-semibold mb-1">Total Dispatched</h6>
              <h3 className="mb-0 fw-bold">{metrics.totalCalls}</h3>
            </div>
          </div>
        </div>
        <div className="col-md-3">
          <div className="card border-0 shadow-sm">
            <div className="card-body">
              <h6 className="text-muted small text-uppercase fw-semibold mb-1">Active Agents</h6>
              <h3 className="mb-0 fw-bold text-primary">{metrics.activeAgents}</h3>
            </div>
          </div>
        </div>
        <div className="col-md-3">
          <div className="card border-0 shadow-sm">
            <div className="card-body">
              <h6 className="text-muted small text-uppercase fw-semibold mb-1">Connect Rate</h6>
              <h3 className="mb-0 fw-bold text-success">{metrics.connectRate}%</h3>
            </div>
          </div>
        </div>
        <div className="col-md-3">
          <div className="card border-0 shadow-sm">
            <div className="card-body">
              <h6 className="text-muted small text-uppercase fw-semibold mb-1">System Load</h6>
              <h3 className="mb-0 fw-bold">{metrics.sysLoad}</h3>
            </div>
          </div>
        </div>
      </div>

      <div className="card border-0 shadow-sm">
        <div className="card-header bg-white border-bottom py-3 d-flex justify-content-between align-items-center">
          <h6 className="mb-0 fw-bold">Active Outbound Legs</h6>
          <button className="btn btn-sm btn-outline-secondary">Filter</button>
        </div>
        <div className="table-responsive">
          <table className="table table-hover align-middle mb-0">
            <thead className="table-light text-muted small">
              <tr>
                <th className="fw-semibold px-4 py-3">Lead Name</th>
                <th className="fw-semibold py-3">Provider</th>
                <th className="fw-semibold py-3">Status</th>
                <th className="fw-semibold py-3">Latest Transcript</th>
                <th className="fw-semibold py-3 text-end px-4">Actions</th>
              </tr>
            </thead>
            <tbody>
              {Object.values(liveCalls).length === 0 ? (
                <tr>
                  <td colSpan="5" className="text-center py-5 text-muted">
                    No active calls routing currently.
                  </td>
                </tr>
              ) : Object.values(liveCalls).map(call => (
                <tr key={call.lead_id}>
                  <td className="px-4 py-3 fw-medium">
                    <div className="d-flex align-items-center gap-2">
                      <div className="bg-light rounded-circle d-flex justify-content-center align-items-center text-secondary" style={{ width:'32px', height:'32px' }}>
                        👤
                      </div>
                      {call.lead_name || 'Unknown Lead'}
                    </div>
                  </td>
                  <td className="py-3">
                    <span className="badge bg-light text-dark shadow-sm border">{call.provider || 'twilio'}</span>
                  </td>
                  <td className="py-3">
                    {getStatusBadge(call.status)}
                  </td>
                  <td className="py-3 text-muted small" style={{ maxWidth: '300px' }}>
                    <div className="text-truncate fst-italic">
                      {call.last_snippet ? `"${call.last_snippet}"` : (call.status === 'completed' ? 'Call finished.' : 'Listening...')}
                    </div>
                  </td>
                  <td className="py-3 px-4 text-end">
                    <button className="btn btn-sm btn-light border shadow-sm">Inspect</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </DashboardLayout>
  );
}
