'use client';
import { useAuth, clientProfile } from '@/context/AuthContext';
import DashboardLayout from '@/components/DashboardLayout';
import { useVoiceSocket } from '@/hooks/useVoiceSocket';
import { useSearchParams } from 'next/navigation';
import { Suspense, useMemo } from 'react';

const DOMAIN_METADATA = {
  'real_estate_sales': { agent: 'Neha', name: 'Real Estate', icon: '🏠' },
  'recruitment': { agent: 'Sarah', name: 'Recruitment', icon: '💼' },
  'healthcare': { agent: 'Maya', name: 'Healthcare', icon: '🩺' },
  'finance': { agent: 'Arjun', name: 'Finance', icon: '📈' },
  'insurance': { agent: 'Ananya', name: 'Insurance', icon: '🛡️' },
  'education': { agent: 'Priya', name: 'Education', icon: '🎓' },
};

function DemoCampaignContent() {
  const { activeClient, currentRole, user } = useAuth();
  const searchParams = useSearchParams();
  const queryAgentId = searchParams ? searchParams.get('agentId') : null;

  const profile = useMemo(() => {
    return currentRole === 'client' && user?.agentId
      ? { name: user.clientName || user.name, agent: user.agentName || 'Assigned Agent', agentId: user.agentId }
      : clientProfile[activeClient] || { name: user?.name || 'Demo User', agent: 'Neha', agentId: 'real_estate_sales' };
  }, [currentRole, user, activeClient]);

  const resolvedAgentId = queryAgentId || profile?.agentId || user?.agentId || 'default';

  // Find dynamic metadata if available
  const domainMeta = DOMAIN_METADATA[resolvedAgentId] || DOMAIN_METADATA[queryAgentId];
  const agentName = domainMeta ? domainMeta.agent : (profile?.agent || user?.agentName || 'Assigned Agent');
  const agentIcon = domainMeta ? domainMeta.icon : '🎙️';
  const domainName = domainMeta ? domainMeta.name : 'Voice Agent';

  const { connect, disconnect, isConnected, statusText, transcripts, events, clearTranscripts } = useVoiceSocket(resolvedAgentId, activeClient);

  const toggleCall = () => {
    if (isConnected) disconnect();
    else connect(true, profile?.name || user?.name || 'Demo User');
  };

  const getLatestCallEvent = () => {
    return events.length > 0 ? events[events.length - 1] : null;
  };

  const latestEvent = getLatestCallEvent();

  const renderResultCard = (result) => {
    if (!result) return null;
    
    // Determine keys to skip in dynamic rows (already displayed or meta-fields)
    const skipKeys = ['transcription', 'duration', 'interested', 'campaign_id', 'lead_id', 'lead_name', 'id', 'created_at', 'client_id', 'provider'];
    
    // Get all other keys that are not null/undefined/empty
    const dynamicFields = Object.keys(result).filter(
      (key) => !skipKeys.includes(key) && result[key] !== null && result[key] !== undefined && result[key] !== ''
    );

    const formatKeyLabel = (key) => {
      return key
        .replace(/_/g, ' ')
        .split(' ')
        .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
    };

    return (
      <div className="card border-0 shadow-sm mt-3 animate-slide-up">
        <div className="card-header bg-dark text-white border-0 py-3">
          <h6 className="mb-0">📋 Lead Summary ({domainName})</h6>
          <small className="text-secondary">Extracted from conversation</small>
        </div>
        <div className="card-body">
          <table className="table table-bordered mb-3" style={{ fontSize: '13px' }}>
            <thead className="table-light text-muted">
              <tr>
                <th>Field</th>
                <th>Extracted Value</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td className="fw-medium text-secondary">Interested</td>
                <td className="fw-bold">
                  {result.interested === 'Yes' || result.interested === true || String(result.interested).toLowerCase() === 'yes' ? (
                    <span className="badge bg-success-subtle text-success border border-success-subtle rounded-pill px-3">Yes</span>
                  ) : (
                    <span className="badge bg-danger-subtle text-danger border border-danger-subtle rounded-pill px-3">{String(result.interested || 'No')}</span>
                  )}
                </td>
              </tr>
              
              {dynamicFields.map((key) => (
                <tr key={key}>
                  <td className="fw-medium text-secondary">{formatKeyLabel(key)}</td>
                  <td className="fw-bold text-dark">{String(result[key])}</td>
                </tr>
              ))}
              
              <tr className="table-light">
                <td className="fw-medium text-secondary">Conversation stats</td>
                <td className="fw-semibold text-secondary">{(result.transcription || []).length} turns · {result.duration || '—'}</td>
              </tr>
            </tbody>
          </table>
          <div className="d-flex align-items-center gap-2 border-top pt-3">
            <span className="bg-success rounded-circle" style={{ width: '8px', height: '8px' }}></span>
            <span className="text-success small fw-medium">Result saved to Call Results tab</span>
          </div>
        </div>
      </div>
    );
  };

  return (
    <DashboardLayout>
      <div className="d-flex justify-content-between align-items-start mb-4">
        <div>
          <h2 className="h4 fw-bold mb-1">🎬 Demo Campaign ({domainName})</h2>
          <p className="text-muted small mb-0">Speak to <strong>{agentName}</strong> — your voice drives the conversation, dashboard updates live.</p>
        </div>
        <div 
          className="rounded-circle mt-2" 
          style={{ width: '12px', height: '12px', background: isConnected ? '#10b981' : '#94a3b8' }} 
          title={isConnected ? 'Connected' : 'Not connected'}
        />
      </div>

      <div className="row g-4">
        <div className="col-md-5">
          <div className="card shadow-sm border-0 h-100">
            <div className="card-body text-center p-5 text-white" style={{ background: 'linear-gradient(135deg, #0f172a, #1a1040)', borderRadius: '12px 12px 0 0' }}>
              <div 
                className="d-flex align-items-center justify-content-center mx-auto mb-4"
                style={{ 
                  width: '110px', height: '110px', fontSize: '44px', borderRadius: '50%', 
                  background: 'radial-gradient(circle at 35% 35%, #a855f7, #7c3aed)',
                  boxShadow: isConnected ? '0 0 0 14px rgba(99,102,241,0.2), 0 0 0 28px rgba(99,102,241,0.08)' : 'none',
                  transition: 'box-shadow 0.4s ease'
                }}
              >
                {agentIcon}
              </div>
              <h5 className="fw-bold mb-1 text-light">{agentName}</h5>
              <p className="text-secondary small mb-4">{statusText}</p>
              <button 
                className={`btn btn-lg w-100 fw-bold border-0 shadow ${isConnected ? 'btn-danger' : 'btn-primary'}`}
                style={{ background: isConnected ? 'linear-gradient(135deg,#ef4444,#dc2626)' : 'linear-gradient(135deg,#7c3aed,#6366f1)' }}
                onClick={toggleCall}
              >
                {isConnected ? 'End Conversation' : '🎬 Start Demo Call'}
              </button>
              <div className="small text-muted mt-3">Allow mic access when prompted</div>
            </div>
          </div>
        </div>

        <div className="col-md-7 d-flex flex-column gap-4">
          <div className="card shadow-sm border-0">
            <div className="card-header bg-white border-bottom py-3 d-flex justify-content-between align-items-center">
              <h6 className="mb-0 fw-bold">Live Feed</h6>
              <span className="small text-muted">{latestEvent ? (latestEvent.type === 'call_completed' ? 'Completed' : 'Active') : 'Waiting for call...'}</span>
            </div>
            <div className="card-body p-4" style={{ minHeight: '120px' }}>
              {!latestEvent && <div className="text-center text-muted small py-3">Press Start Demo Call to see live updates</div>}
              
              {latestEvent && (
                <div className={`p-3 border rounded-3 ${latestEvent.type === 'call_completed' ? 'bg-success-subtle border-success-subtle' : 'bg-white'}`}>
                  <div className="d-flex justify-content-between align-items-center mb-2">
                    <span className="fw-bold small">👤 {latestEvent.leadName || profile?.name || user?.name || 'Demo User'}</span>
                    <span className={`badge ${latestEvent.type === 'call_completed' ? 'bg-success' : 'bg-primary border'}`}>
                      {latestEvent.type.replace('call_', '')}
                    </span>
                  </div>
                  {latestEvent.snippet && (
                    <div className="small text-secondary fst-italic mt-2">&quot;{latestEvent.snippet}&quot;</div>
                  )}
                  {latestEvent.type === 'call_completed' && (
                    <div className="small text-success mt-2 fw-medium">
                      ✓ {latestEvent.transcripts?.length || 0} turns — result saved to Call Results
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          <div className="card shadow-sm border-0 flex-grow-1">
            <div className="card-header bg-white border-bottom py-3 d-flex justify-content-between align-items-center">
              <h6 className="mb-0 fw-bold">Live Transcript</h6>
              <button className="btn btn-sm btn-link text-muted text-decoration-none shadow-none" onClick={clearTranscripts}>Clear</button>
            </div>
            <div className="card-body p-4 bg-light overflow-auto" style={{ minHeight: '260px', maxHeight: '400px' }}>
              {transcripts.length === 0 && <div className="text-center text-muted small py-5">Transcript will appear as you speak</div>}
              {transcripts.map((msg, i) => {
                const isAgent = msg.speaker === 'agent';
                return (
                  <div key={i} className={`p-3 rounded-3 mb-2 shadow-sm ${isAgent ? 'bg-white text-dark border-start border-primary border-4' : 'bg-success-subtle text-dark border-start border-success border-4'}`}>
                    <div className="small text-uppercase fw-bold text-muted mb-1" style={{ letterSpacing: '0.5px', fontSize: '10px' }}>
                      {isAgent ? `🤖 ${agentName}` : '👤 You'}
                    </div>
                    <div className="small">{msg.text}</div>
                  </div>
                );
              })}
            </div>
          </div>

          {latestEvent?.type === 'call_completed' && renderResultCard(latestEvent.result)}
        </div>
      </div>
    </DashboardLayout>
  );
}

export default function DemoCampaign() {
  return (
    <Suspense fallback={
      <DashboardLayout>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '50vh' }}>
          <div style={{ width: '32px', height: '32px', border: '3px solid #e5e7eb', borderTopColor: '#6366f1', borderRadius: '50%', animation: 'spin 0.7s linear infinite' }} />
        </div>
      </DashboardLayout>
    }>
      <DemoCampaignContent />
    </Suspense>
  );
}
