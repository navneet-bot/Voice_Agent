'use client';
import { useAuth, clientProfile } from '@/context/AuthContext';
import DashboardLayout from '@/components/DashboardLayout';
import { useVoiceSocket } from '@/hooks/useVoiceSocket';

export default function TalkLive() {
  const { activeClient } = useAuth();
  const profile = clientProfile[activeClient];
  const agentId = profile?.agentId || 'default';
  
  const { connect, disconnect, isConnected, statusText, transcripts, clearTranscripts } = useVoiceSocket(agentId, activeClient);

  const toggleCall = () => {
    if (isConnected) disconnect();
    else connect(false); // isDemo = false
  };

  return (
    <DashboardLayout>
      <div className="d-flex justify-content-between align-items-start mb-4">
        <div>
          <h2 className="h4 fw-bold mb-1">Talk Live</h2>
          <p className="text-muted small mb-0">Test your agent ({profile?.agent}) directly from your browser mic instantly.</p>
        </div>
        <div 
          className="rounded-circle mt-2" 
          style={{ width: '12px', height: '12px', background: isConnected ? '#10b981' : '#94a3b8' }} 
          title={isConnected ? 'Connected' : 'Not connected'}
        />
      </div>

      <div className="row g-4">
        <div className="col-md-4">
          <div className="card shadow-sm border-0">
            <div className="card-body text-center p-5">
              <div 
                className="d-flex align-items-center justify-content-center mx-auto mb-4 text-white"
                style={{ 
                  width: '90px', height: '90px', fontSize: '32px', borderRadius: '50%', 
                  background: 'linear-gradient(135deg, #7c3aed, #4c1d95)',
                  boxShadow: isConnected ? '0 0 0 10px rgba(99,102,241,0.2), 0 0 0 20px rgba(99,102,241,0.08)' : 'none',
                  transition: 'box-shadow 0.4s ease'
                }}
              >
                🎙️
              </div>
              <h5 className="fw-bold">{profile?.agent}</h5>
              <p className="text-muted small mb-4">{statusText}</p>
              <button 
                className={`btn btn-lg w-100 fw-bold border-0 shadow-sm ${isConnected ? 'btn-danger' : 'btn-dark'}`}
                onClick={toggleCall}
              >
                {isConnected ? 'End Conversation' : 'Connect & Start Talking'}
              </button>
            </div>
            <div className="card-footer bg-light border-0 p-3 text-center">
              <div className="small text-muted">Use this tab for sandbox testing before launching campaigns.</div>
            </div>
          </div>
        </div>

        <div className="col-md-8">
          <div className="card shadow-sm border-0 h-100 d-flex flex-column">
            <div className="card-header bg-white border-bottom py-3 d-flex justify-content-between align-items-center">
              <h6 className="mb-0 fw-bold">Live Transcript</h6>
              <button className="btn btn-sm btn-link text-muted text-decoration-none shadow-none" onClick={clearTranscripts}>Clear</button>
            </div>
            <div className="card-body p-4 bg-light overflow-auto flex-grow-1" style={{ minHeight: '400px' }}>
              {transcripts.length === 0 && <div className="text-center text-muted small py-5">Speech will appear here as you talk</div>}
              {transcripts.map((msg, i) => {
                const isAgent = msg.speaker === 'agent';
                return (
                  <div key={i} className={`p-3 rounded-3 mb-2 shadow-sm ${isAgent ? 'bg-white text-dark border-start border-primary border-4' : 'bg-success-subtle text-dark border-start border-success border-4'}`}>
                    <div className="small text-uppercase fw-bold text-muted mb-1" style={{ letterSpacing: '0.5px', fontSize: '10px' }}>
                      {isAgent ? '🤖 Agent' : '👤 You'}
                    </div>
                    <div className="small">{msg.text}</div>
                  </div>
                );
              })}
            </div>
            <div className="card-footer bg-white border-top p-3 small text-muted text-center">
              Low-latency WebRTC Audio via Pipecat and Groq Whisper.
            </div>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
