'use client';
import { useState, useEffect } from 'react';
import DashboardLayout from '@/components/DashboardLayout';
import { useAuth } from '@/context/AuthContext';
import { getProviderLabel } from '@/lib/providerDisplay';

const AGENT_TYPE_TEMPLATES = {
  real_estate_sales: {
    label: 'Real Estate Sales',
    fields: 'interested, budget, location, property_type, timeline, callback',
    prompt: `You are a professional real estate sales voice agent for a property advisory team.

Primary goal:
Qualify the lead for buying, renting, or investing in residential property and capture the next best action.

Conversation style:
Be warm, concise, consultative, and natural. Ask one question at a time. Do not sound like a form. Use the user's language style when possible: English, Hindi, Marathi, or Hinglish.

Discovery questions:
1. Confirm whether they are looking to buy, rent, or invest.
2. Ask preferred location or project area.
3. Ask budget range.
4. Ask property type such as 1 BHK, 2 BHK, 3 BHK, villa, plot, or commercial.
5. Ask timeline such as immediate, this month, 3 months, or just exploring.
6. Ask if they want a callback, site visit, WhatsApp details, or brochure.

Rules:
Never overpromise pricing, availability, loan approval, legal clearance, or possession date. If the user asks for exact details, say the specialist will verify and share updated information.

Final outcome:
Summarize the requirement in one sentence and confirm the follow-up action.`
  },
  finance: {
    label: 'Finance Advisory',
    fields: 'interested, product_interest, income_range, loan_amount, timeline, callback',
    prompt: `You are a compliant finance advisory voice agent.

Primary goal:
Understand the customer's interest in financial products such as personal loans, business loans, credit cards, insurance, or investments and qualify them for a human advisor.

Conversation style:
Be calm, trustworthy, and precise. Ask one question at a time. Avoid pressure tactics. Keep the conversation short and respectful.

Discovery questions:
1. Ask which financial product they are interested in.
2. Ask the purpose, required amount, or preferred plan.
3. Ask broad eligibility details only when appropriate, such as income range or employment type.
4. Ask their timeline for taking a decision.
5. Ask for permission to arrange a callback from an advisor.

Compliance rules:
Do not guarantee approval, returns, interest rates, tax benefits, or eligibility. Do not collect sensitive data such as OTPs, full card numbers, passwords, bank PINs, Aadhaar numbers, or account login details.

Final outcome:
Summarize the customer's need and confirm that an authorized advisor will follow up.`
  },
  insurance: {
    label: 'Insurance Renewal',
    fields: 'interested, policy_type, renewal_date, coverage_need, family_members, callback',
    prompt: `You are an insurance renewal and advisory voice agent.

Primary goal:
Help the customer review or renew insurance coverage and identify whether they need a callback from an advisor.

Conversation style:
Be empathetic, clear, and low-pressure. Use plain language. Ask one question at a time.

Discovery questions:
1. Ask whether they are interested in health, life, motor, or business insurance.
2. Ask if this is a renewal, new policy, or comparison request.
3. Ask renewal date or urgency.
4. Ask basic coverage preference such as individual, family, or vehicle.
5. Ask whether they want plan options shared on WhatsApp/email or a callback.

Compliance rules:
Do not guarantee claim approval, premium, coverage, or policy issuance. Do not collect sensitive documents or payment details over the call.

Final outcome:
Confirm the requested insurance type, urgency, and preferred follow-up mode.`
  },
  education: {
    label: 'Education Counselling',
    fields: 'interested, course_interest, education_level, city, budget, callback',
    prompt: `You are an education counselling voice agent.

Primary goal:
Understand the student's course interest and connect them with the right counsellor.

Conversation style:
Be encouraging, patient, and clear. Ask one question at a time. Support parents and students without sounding pushy.

Discovery questions:
1. Ask which course, program, exam, or career path they are interested in.
2. Ask current education level.
3. Ask preferred city, online/offline preference, and timeline.
4. Ask budget or fee range only if the conversation naturally allows it.
5. Ask whether a counsellor should call back.

Rules:
Do not guarantee admission, scholarship, visa approval, placement, or exam results.

Final outcome:
Summarize the student requirement and confirm the counselling follow-up.`
  }
};

const DEFAULT_AGENT_TYPE = 'real_estate_sales';
const CARTESIA_FEMALE_VOICES = [
  {
    label: 'Hinglish Speaking Lady - Indian multilingual (recommended)',
    value: '95d51f79-c397-46f9-b49a-23763d3eaa2d'
  },
  {
    label: 'Indian Customer Support Lady - phone support',
    value: 'ff1bb1a9-c582-4570-9670-5f46169d0fc8'
  },
  {
    label: 'Indian Lady - Indian accent fallback',
    value: '3b554273-4299-48b9-9aaf-eefd438e3941'
  },
  {
    label: 'Hindi Narrator Woman - Hindi-focused',
    value: 'c1abd502-9231-4558-a054-10ac950c356d'
  },
  {
    label: 'Katie - US English voice agent fallback',
    value: 'f786b574-daa5-4673-aa0c-cbe3e8534c02'
  },
  {
    label: 'Tessa - US English expressive fallback',
    value: '6ccbfb76-1fc6-48f7-b71d-91ac6298247b'
  }
];
const DEFAULT_CARTESIA_VOICE_ID = CARTESIA_FEMALE_VOICES[0].value;

const makeInitialFormData = (overrides = {}) => ({
  name: '',
  voice: '11labs-06nek6zjTCD1vCbtc8bc',
  language: 'English',
  max_duration: 300,
  provider: 'twilio',
  stt_provider: 'groq',
  tts_provider: 'edge',
  cartesia_voice_id: DEFAULT_CARTESIA_VOICE_ID,
  assigned_email: '',
  agent_type: DEFAULT_AGENT_TYPE,
  script: AGENT_TYPE_TEMPLATES[DEFAULT_AGENT_TYPE].prompt,
  data_fields: AGENT_TYPE_TEMPLATES[DEFAULT_AGENT_TYPE].fields,
  ...overrides
});

const formDataFromAgent = (agent) => {
  const agentType = agent.agent_type || DEFAULT_AGENT_TYPE;
  const template = AGENT_TYPE_TEMPLATES[agentType] || AGENT_TYPE_TEMPLATES[DEFAULT_AGENT_TYPE];
  return makeInitialFormData({
    name: agent.name || '',
    voice: agent.voice || '11labs-06nek6zjTCD1vCbtc8bc',
    language: agent.language || 'English',
    max_duration: agent.max_duration || 300,
    provider: agent.provider || 'twilio',
    stt_provider: agent.stt_provider || 'groq',
    tts_provider: agent.tts_provider || 'edge',
    cartesia_voice_id: agent.cartesia_voice_id || DEFAULT_CARTESIA_VOICE_ID,
    assigned_email: agent.assigned_email || '',
    agent_type: agentType,
    script: agent.script || template.prompt,
    data_fields: Array.isArray(agent.data_fields) ? agent.data_fields.join(', ') : agent.data_fields || template.fields
  });
};

export default function AgentsPage() {
  const { user } = useAuth();
  const [agents, setAgents] = useState([]);
  const [showModal, setShowModal] = useState(false);
  const [modalMode, setModalMode] = useState('create');
  const [editingAgentId, setEditingAgentId] = useState(null);
  const [loading, setLoading] = useState(true);
  
  const [formData, setFormData] = useState(makeInitialFormData);

  const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  const fetchAgents = async () => {
    setLoading(true);
    try {
      const ownAgentsQuery = user?.role === 'client' && user?.email
        ? `?user_email=${encodeURIComponent(user.email)}`
        : '';
      const res = await fetch(`${API}/api/agents${ownAgentsQuery}`);
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
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchAgents();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const openCreateModal = () => {
    setModalMode('create');
    setEditingAgentId(null);
    setFormData(makeInitialFormData());
    setShowModal(true);
  };

  const openEditModal = (agent) => {
    setModalMode('edit');
    setEditingAgentId(agent.id);
    setFormData(formDataFromAgent(agent));
    setShowModal(true);
  };

  const closeModal = () => {
    setShowModal(false);
    setEditingAgentId(null);
    setModalMode('create');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const payload = {
      ...formData,
      data_fields: formData.data_fields.split(',').map(s => s.trim()).filter(Boolean)
    };
    const isEdit = modalMode === 'edit' && editingAgentId;
    const url = isEdit ? `${API}/api/agents/${editingAgentId}` : `${API}/api/agents`;

    try {
      const res = await fetch(url, {
        method: isEdit ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        closeModal();
        setFormData(makeInitialFormData({
          agent_type: formData.agent_type,
          script: AGENT_TYPE_TEMPLATES[formData.agent_type]?.prompt || AGENT_TYPE_TEMPLATES[DEFAULT_AGENT_TYPE].prompt,
          data_fields: AGENT_TYPE_TEMPLATES[formData.agent_type]?.fields || AGENT_TYPE_TEMPLATES[DEFAULT_AGENT_TYPE].fields
        }));
        fetchAgents();
      } else {
        alert(isEdit ? "Failed to update agent" : "Failed to create agent");
      }
    } catch (e) {
      console.error(e);
      alert("Error connecting to backend");
    }
  };

  const handleAgentTypeChange = (agentType) => {
    const template = AGENT_TYPE_TEMPLATES[agentType] || AGENT_TYPE_TEMPLATES[DEFAULT_AGENT_TYPE];
    setFormData({
      ...formData,
      agent_type: agentType,
      script: template.prompt,
      data_fields: template.fields
    });
  };

  return (
    <DashboardLayout>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <div>
          <h2 className="h4 fw-bold mb-1">Voice Agents</h2>
          <p className="text-muted small mb-0">Configure AI agent personas and voices</p>
        </div>
        {user?.role === 'admin' && (
          <button className="btn btn-primary btn-sm px-3 shadow-sm" onClick={openCreateModal}>
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
            <p className="small">Click &apos;Create Agent&apos; to build your first AI persona.</p>
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
                  <p className="small text-muted mb-3"><strong>Provider:</strong> {getProviderLabel('telephony', agent.provider || 'twilio')}</p>
                  <p className="small text-muted mb-2"><strong>Type:</strong> {AGENT_TYPE_TEMPLATES[agent.agent_type]?.label || agent.agent_type || 'Real Estate Sales'}</p>
                  <p className="small text-muted mb-2"><strong>Assigned:</strong> {agent.assigned_email || 'Unassigned'}</p>
                  <p className="small text-muted mb-2"><strong>STT:</strong> {getProviderLabel('stt', agent.stt_provider || 'groq')}</p>
                  <p className="small text-muted mb-3"><strong>TTS:</strong> {getProviderLabel('tts', agent.tts_provider || 'edge')}</p>
                  {agent.tts_provider === 'cartesia' && (
                    <p className="small text-muted mb-3"><strong>Premium Voice:</strong> {CARTESIA_FEMALE_VOICES.find(v => v.value === agent.cartesia_voice_id)?.label || agent.cartesia_voice_id || 'Hinglish Speaking Lady'}</p>
                  )}
                  
                  <div className="small text-muted">
                    <strong className="d-block mb-1">Extracted Fields:</strong>
                    <div className="d-flex flex-wrap gap-1">
                      {agent.data_fields?.map((field, i) => (
                        <span key={i} className="badge bg-secondary-subtle text-secondary border">{field}</span>
                      ))}
                    </div>
                  </div>
                </div>
                <div className="card-footer bg-white border-top py-3">
                  <div className="d-flex justify-content-between align-items-center gap-2">
                    <small className="text-muted">ID: {(agent.id || agent.agent_id || '').substring(0,8)}...</small>
                    {user?.role === 'admin' && (
                      <button type="button" className="btn btn-outline-primary btn-sm" onClick={() => openEditModal(agent)}>
                        Edit
                      </button>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modal for Creating or Editing Agent */}
      {showModal && (
        <div className="modal show d-block" tabIndex="-1" style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
          <div className="modal-dialog modal-lg modal-dialog-centered">
            <div className="modal-content border-0 shadow">
              <div className="modal-header border-bottom-0 pb-0">
                <h5 className="modal-title fw-bold">{modalMode === 'edit' ? 'Edit Voice Agent' : 'Create New Voice Agent'}</h5>
                <button type="button" className="btn-close shadow-none" onClick={closeModal}></button>
              </div>
              <div className="modal-body">
                <form onSubmit={handleSubmit}>
                  <div className="row g-3 mb-3">
                    <div className="col-md-6">
                      <label className="form-label small fw-bold">Agent Name</label>
                      <input type="text" className="form-control" required value={formData.name} onChange={e => setFormData({...formData, name: e.target.value})} placeholder="e.g. Sales Rep Priya" />
                    </div>
                    <div className="col-md-6">
                      <label className="form-label small fw-bold">Assign to User Email</label>
                      <input type="email" className="form-control" required value={formData.assigned_email} onChange={e => setFormData({...formData, assigned_email: e.target.value})} placeholder="client@example.com" />
                      <div className="form-text">This agent will be isolated to this user&apos;s client account.</div>
                    </div>
                  </div>

                  <div className="row g-3 mb-3">
                    <div className="col-md-6">
                      <label className="form-label small fw-bold">Agent Type</label>
                      <select className="form-select" value={formData.agent_type} onChange={e => handleAgentTypeChange(e.target.value)}>
                        {Object.entries(AGENT_TYPE_TEMPLATES).map(([value, config]) => (
                          <option key={value} value={value}>{config.label}</option>
                        ))}
                      </select>
                      <div className="form-text">Changing this loads a detailed editable prompt template.</div>
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
                        <option value="twilio">{getProviderLabel('telephony', 'twilio')}</option>
                        <option value="demo">{getProviderLabel('telephony', 'demo')}</option>
                      </select>
                    </div>
                    <div className="col-md-4">
                      <label className="form-label small fw-bold">Max Duration (sec)</label>
                      <input type="number" className="form-control" value={formData.max_duration} onChange={e => setFormData({...formData, max_duration: parseInt(e.target.value) || 300})} />
                    </div>
                  </div>

                  <div className="row g-3 mb-3">
                    <div className="col-md-6">
                      <label className="form-label small fw-bold">STT Engine</label>
                      <select className="form-select" value={formData.stt_provider} onChange={e => setFormData({...formData, stt_provider: e.target.value})}>
                        <option value="groq">{getProviderLabel('stt', 'groq')} (Default)</option>
                        <option value="deepgram">{getProviderLabel('stt', 'deepgram')}</option>
                      </select>
                      <div className="form-text">Enhanced transcription is enabled for this agent when selected and API keys exist.</div>
                    </div>
                    <div className="col-md-6">
                      <label className="form-label small fw-bold">TTS Engine</label>
                      <select className="form-select" value={formData.tts_provider} onChange={e => setFormData({...formData, tts_provider: e.target.value})}>
                        <option value="edge">{getProviderLabel('tts', 'edge')} (Default)</option>
                        <option value="cartesia">{getProviderLabel('tts', 'cartesia')}</option>
                      </select>
                      <div className="form-text">Premium voice synthesis is enabled for this agent when selected.</div>
                    </div>
                  </div>

                  {formData.tts_provider === 'cartesia' && (
                    <div className="mb-3">
                      <label className="form-label small fw-bold">Premium Voice</label>
                      <select className="form-select" value={formData.cartesia_voice_id} onChange={e => setFormData({...formData, cartesia_voice_id: e.target.value})}>
                        {CARTESIA_FEMALE_VOICES.map((voice) => (
                          <option key={voice.value} value={voice.value}>{voice.label}</option>
                        ))}
                      </select>
                      <div className="form-text">Recommended for native Indian-style English, Hindi, Hinglish, and Marathi tests. Each agent stores its own selected voice.</div>
                    </div>
                  )}

                  <div className="mb-3">
                    <label className="form-label small fw-bold">Data Extraction Fields (Comma separated)</label>
                    <input type="text" className="form-control" value={formData.data_fields} onChange={e => setFormData({...formData, data_fields: e.target.value})} placeholder="interested, budget, location" />
                  </div>

                  <div className="mb-4">
                    <label className="form-label small fw-bold">Agent Prompt / Script (Editable)</label>
                    <textarea className="form-control" rows="11" required value={formData.script} onChange={e => setFormData({...formData, script: e.target.value})} placeholder="You are an AI assistant..."></textarea>
                  </div>

                  <div className="d-flex justify-content-end gap-2">
                    <button type="button" className="btn btn-light border" onClick={closeModal}>Cancel</button>
                    <button type="submit" className="btn btn-primary px-4">{modalMode === 'edit' ? 'Save Changes' : 'Create Agent'}</button>
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
