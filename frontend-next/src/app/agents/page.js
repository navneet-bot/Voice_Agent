'use client';
import { useState, useEffect } from 'react';
import DashboardLayout from '@/components/DashboardLayout';
import FlowPreviewModal from '@/components/FlowPreviewModal';
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
const FLOW_VISUALIZATION_ENABLED = process.env.NEXT_PUBLIC_FLOW_VISUALIZATION_ENABLED === 'true';
const SCRAPE_GENERATE_SCRIPT_ENABLED = process.env.NEXT_PUBLIC_SCRAPE_GENERATE_SCRIPT_ENABLED === 'true';
const SCRAPE_WORKER_V1_ENABLED = process.env.NEXT_PUBLIC_SCRAPE_WORKER_V1_ENABLED === 'true';
const SCRAPE_POLL_INTERVAL_MS = 1500;
const SCRAPE_POLL_ATTEMPTS = 12;
const SCRAPE_REUSE_FINAL_STATUSES = ['completed', 'draft_ready'];
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

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

function qualityClass(level) {
  if (level === 'high') return 'bg-success-subtle text-success border-success-subtle';
  if (level === 'medium') return 'bg-primary-subtle text-primary border-primary-subtle';
  if (level === 'low') return 'bg-warning-subtle text-warning border-warning-subtle';
  return 'bg-secondary-subtle text-secondary border-secondary-subtle';
}

function draftQuality(draft) {
  return draft?.knowledge?.quality || null;
}

function sourceEvidenceFromKnowledge(knowledge) {
  const values = [];
  const add = (items) => {
    (items || []).forEach((item) => {
      if (typeof item === 'string') values.push(item);
    });
  };
  if (knowledge?.source_url) values.push(knowledge.source_url);
  add(knowledge?.company?.evidence);
  (knowledge?.products_or_services || []).forEach((item) => add(item.evidence));
  (knowledge?.value_propositions || []).forEach((item) => add(item.evidence));
  (knowledge?.faqs || []).forEach((item) => add(item.evidence));
  (knowledge?.pages_crawled || []).forEach((page) => {
    if (page?.url) values.push(page.url);
  });
  return [...new Set(values.filter(Boolean))].slice(0, 6);
}

function contentInventoryItems(knowledge) {
  const pageTypes = knowledge?.content_inventory?.page_types || {};
  return Object.entries(pageTypes)
    .filter(([, count]) => Number(count) > 0)
    .sort(([left], [right]) => left.localeCompare(right))
    .slice(0, 8);
}

function guidanceSummary(knowledge) {
  const questions = (knowledge?.qualification_questions || []).filter(Boolean).slice(0, 4);
  const objections = (knowledge?.objections || [])
    .filter((item) => item?.intent || item?.guidance)
    .slice(0, 4);
  const faqs = (knowledge?.faqs || [])
    .filter((item) => item?.question)
    .slice(0, 4);
  return {
    questions,
    objections,
    faqs,
    hasItems: Boolean(questions.length || objections.length || faqs.length),
  };
}

function ConversationGuidance({ knowledge }) {
  const guidance = guidanceSummary(knowledge);
  if (!guidance.hasItems) return null;

  return (
    <div className="border-top mt-3 pt-3 small">
      <div className="text-muted mb-1">Conversation Guidance</div>
      <div className="row g-2">
        {guidance.questions.length > 0 && (
          <div className="col-md-4">
            <div className="fw-semibold mb-1">Qualification</div>
            <ul className="mb-0 ps-3">
              {guidance.questions.map((question, index) => (
                <li key={`${question}-${index}`}>{question}</li>
              ))}
            </ul>
          </div>
        )}
        {guidance.objections.length > 0 && (
          <div className="col-md-4">
            <div className="fw-semibold mb-1">Objections</div>
            <ul className="mb-0 ps-3">
              {guidance.objections.map((item, index) => (
                <li key={`${item.intent || 'objection'}-${index}`}>
                  <span className="text-capitalize">{String(item.intent || 'objection').replaceAll('_', ' ')}</span>
                  {item.guidance ? `: ${item.guidance}` : ''}
                </li>
              ))}
            </ul>
          </div>
        )}
        {guidance.faqs.length > 0 && (
          <div className="col-md-4">
            <div className="fw-semibold mb-1">FAQs</div>
            <ul className="mb-0 ps-3">
              {guidance.faqs.map((item, index) => (
                <li key={`${item.question}-${index}`}>{item.question}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}

export default function AgentsPage() {
  const { user } = useAuth();
  const [agents, setAgents] = useState([]);
  const [showModal, setShowModal] = useState(false);
  const [modalMode, setModalMode] = useState('create');
  const [editingAgentId, setEditingAgentId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [flowPreviewAgent, setFlowPreviewAgent] = useState(null);
  const [flowPreview, setFlowPreview] = useState(null);
  const [flowPreviewLoading, setFlowPreviewLoading] = useState(false);
  const [flowPreviewError, setFlowPreviewError] = useState('');
  const [flowPreviewReadOnly, setFlowPreviewReadOnly] = useState(false);
  const [scrapeAgent, setScrapeAgent] = useState(null);
  const [scrapeUrl, setScrapeUrl] = useState('');
  const [scrapeJob, setScrapeJob] = useState(null);
  const [scrapeDraft, setScrapeDraft] = useState(null);
  const [scrapeDraftHistory, setScrapeDraftHistory] = useState([]);
  const [scrapeHistoryLoading, setScrapeHistoryLoading] = useState(false);
  const [scrapeStatus, setScrapeStatus] = useState('');
  const [scrapeError, setScrapeError] = useState('');
  const [scrapeLoading, setScrapeLoading] = useState(false);
  const [scrapeApplyLoading, setScrapeApplyLoading] = useState(false);
  const [scrapePreflightLoading, setScrapePreflightLoading] = useState(false);
  const [scrapeApplyMessage, setScrapeApplyMessage] = useState('');
  
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

  const closeFlowPreview = () => {
    setFlowPreviewAgent(null);
    setFlowPreview(null);
    setFlowPreviewError('');
    setFlowPreviewLoading(false);
    setFlowPreviewReadOnly(false);
  };

  const openScrapeModal = (agent) => {
    setScrapeAgent(agent);
    setScrapeUrl('');
    setScrapeJob(null);
    setScrapeDraft(null);
    setScrapeDraftHistory([]);
    setScrapeHistoryLoading(false);
    setScrapeStatus('');
    setScrapeError('');
    setScrapeApplyMessage('');
    setScrapeApplyLoading(false);
    setScrapePreflightLoading(false);
    setScrapeLoading(false);
    loadScrapeDraftHistory(agent);
  };

  const closeScrapeModal = () => {
    if (scrapeLoading) return;
    setScrapeAgent(null);
    setScrapeUrl('');
    setScrapeJob(null);
    setScrapeDraft(null);
    setScrapeDraftHistory([]);
    setScrapeHistoryLoading(false);
    setScrapeStatus('');
    setScrapeError('');
    setScrapeApplyMessage('');
    setScrapeApplyLoading(false);
    setScrapePreflightLoading(false);
  };

  const buildTenantHeaders = (json = false) => {
    const headers = json ? { 'Content-Type': 'application/json' } : {};
    if (user?.clientId) headers['X-Tenant-ID'] = user.clientId;
    return headers;
  };

  const loadScrapeDraftHistory = async (agent) => {
    if (!agent?.id || !SCRAPE_GENERATE_SCRIPT_ENABLED) return;
    setScrapeHistoryLoading(true);
    try {
      const params = new URLSearchParams({ agentId: agent.id });
      if (user?.clientId || agent.client_id) {
        params.set('clientId', user?.clientId || agent.client_id);
      }
      const res = await fetch(`${API}/api/intelligence/script-drafts?${params.toString()}`, {
        headers: buildTenantHeaders(),
      });
      if (!res.ok) return;
      const body = await res.json();
      setScrapeDraftHistory(Array.isArray(body.items) ? body.items : []);
    } catch (err) {
      console.error('Failed to load generated drafts', err);
    } finally {
      setScrapeHistoryLoading(false);
    }
  };

  const openFlowPreview = async (agent) => {
    setFlowPreviewAgent(agent);
    setFlowPreview(null);
    setFlowPreviewError('');
    setFlowPreviewLoading(true);
    setFlowPreviewReadOnly(false);
    try {
      const headers = user?.clientId ? { 'X-Tenant-ID': user.clientId } : {};
      const res = await fetch(`${API}/api/agents/${agent.id}/flow-preview`, { headers });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || 'Flow preview is unavailable');
      }
      setFlowPreview(await res.json());
    } catch (err) {
      setFlowPreviewError(err.message || 'Flow preview is unavailable');
    } finally {
      setFlowPreviewLoading(false);
    }
  };

  const saveFlowDraft = async (draft) => {
    if (!flowPreviewAgent) return;
    const headers = { 'Content-Type': 'application/json' };
    if (user?.clientId) headers['X-Tenant-ID'] = user.clientId;
    const res = await fetch(`${API}/api/agents/${flowPreviewAgent.id}/flow-v2-draft`, {
      method: 'PUT',
      headers,
      body: JSON.stringify(draft)
    });
    const body = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(body.detail || 'Flow save failed');
    }
    setFlowPreview(body);
  };

  const parseApiError = async (res, fallback) => {
    const body = await res.json().catch(() => ({}));
    return body.detail || fallback;
  };

  const pollScrapeJob = async (jobId) => {
    let latest = null;
    for (let attempt = 0; attempt < SCRAPE_POLL_ATTEMPTS; attempt += 1) {
      await wait(SCRAPE_POLL_INTERVAL_MS);
      const res = await fetch(`${API}/api/intelligence/scrape-jobs/${jobId}`, {
        headers: buildTenantHeaders(),
      });
      if (!res.ok) break;
      latest = await res.json();
      setScrapeJob(latest);
      setScrapeStatus(`Scrape ${latest.status || 'queued'}`);
      if (['completed', 'failed', 'draft_ready', 'cancelled'].includes(latest.status)) break;
    }
    return latest;
  };

  const handleGenerateFromWebsite = async (event) => {
    event.preventDefault();
    if (!scrapeAgent || !scrapeUrl.trim()) return;
    setScrapeLoading(true);
    setScrapeError('');
    setScrapeDraft(null);
    setScrapeJob(null);
    try {
      setScrapeStatus('Creating scrape job');
      const jobRes = await fetch(`${API}/api/intelligence/scrape-jobs`, {
        method: 'POST',
        headers: buildTenantHeaders(true),
        body: JSON.stringify({
          url: scrapeUrl.trim(),
          agentId: scrapeAgent.id,
          clientId: user?.clientId || scrapeAgent.client_id || null,
          requestedBy: user?.email || '',
          reuseExisting: true,
        }),
      });
      if (!jobRes.ok) {
        throw new Error(await parseApiError(jobRes, 'Scrape job could not be created'));
      }
      const job = await jobRes.json();
      setScrapeJob(job);
      const reusedJob = Boolean(job.cache?.reused);
      if (reusedJob) {
        setScrapeStatus(`Using cached ${job.status || 'queued'} scrape job`);
      }

      if (SCRAPE_WORKER_V1_ENABLED && !SCRAPE_REUSE_FINAL_STATUSES.includes(job.status)) {
        setScrapeStatus('Dispatching scrape worker');
        const dispatchRes = await fetch(`${API}/api/intelligence/scrape-jobs/${job.id}/dispatch`, {
          method: 'POST',
          headers: buildTenantHeaders(true),
          body: JSON.stringify({
            industryHint: scrapeAgent.agent_type || DEFAULT_AGENT_TYPE,
            requestedBy: user?.email || '',
          }),
        });
        if (!dispatchRes.ok) {
          throw new Error(await parseApiError(dispatchRes, 'Scrape worker could not be dispatched'));
        }
        await dispatchRes.json().catch(() => ({}));
        const latest = await pollScrapeJob(job.id);
        if (latest?.status === 'failed') {
          throw new Error(latest.error || 'Scrape worker failed');
        }
        if (latest?.status === 'cancelled') {
          throw new Error(latest.error || 'Scrape job was cancelled');
        }
      }

      setScrapeStatus('Creating draft');
      const draftRes = await fetch(`${API}/api/intelligence/script-drafts`, {
        method: 'POST',
        headers: buildTenantHeaders(true),
        body: JSON.stringify({
          jobId: job.id,
          agentId: scrapeAgent.id,
          industryHint: scrapeAgent.agent_type || DEFAULT_AGENT_TYPE,
        }),
      });
      if (!draftRes.ok) {
        throw new Error(await parseApiError(draftRes, 'Script draft could not be created'));
      }
      const draft = await draftRes.json();
      setScrapeDraft(draft);
      setScrapeDraftHistory((items) => [
        draft,
        ...items.filter((item) => item.id !== draft.id),
      ]);
      setScrapeStatus('Draft ready');
    } catch (err) {
      setScrapeError(err.message || 'Website script generation failed');
      setScrapeStatus('');
    } finally {
      setScrapeLoading(false);
    }
  };

  const handleApplyGeneratedDraft = async (draftToApply = scrapeDraft) => {
    if (!draftToApply || !scrapeAgent) return;
    setScrapeApplyLoading(true);
    setScrapeError('');
    setScrapeApplyMessage('');
    try {
      const res = await fetch(`${API}/api/intelligence/script-drafts/${draftToApply.id}/apply-flow-draft`, {
        method: 'POST',
        headers: buildTenantHeaders(true),
        body: JSON.stringify({
          reviewAcknowledged: true,
          reviewNotes: 'Saved from agents generate script review modal',
        }),
      });
      if (!res.ok) {
        throw new Error(await parseApiError(res, 'Generated draft could not be applied'));
      }
      const preview = await res.json();
      setScrapeApplyMessage('Review recorded. Draft saved to agent flow.');
      setFlowPreviewAgent(scrapeAgent);
      setFlowPreview(preview);
      setFlowPreviewError('');
      setFlowPreviewLoading(false);
      setFlowPreviewReadOnly(false);
      setScrapeAgent(null);
      setScrapeUrl('');
      setScrapeJob(null);
      setScrapeDraft(null);
      setScrapeStatus('');
      setScrapeError('');
    } catch (err) {
      setScrapeError(err.message || 'Generated draft could not be applied');
    } finally {
      setScrapeApplyLoading(false);
    }
  };

  const handlePreflightGeneratedDraft = async (draftToPreflight = scrapeDraft) => {
    if (!draftToPreflight || !scrapeAgent || !FLOW_VISUALIZATION_ENABLED) return;
    setScrapePreflightLoading(true);
    setScrapeError('');
    setScrapeApplyMessage('');
    setFlowPreviewLoading(true);
    setFlowPreviewError('');
    try {
      const res = await fetch(`${API}/api/intelligence/script-drafts/${draftToPreflight.id}/preflight-flow-draft`, {
        method: 'POST',
        headers: buildTenantHeaders(),
      });
      if (!res.ok) {
        throw new Error(await parseApiError(res, 'Generated draft preflight failed'));
      }
      const preview = await res.json();
      setFlowPreviewAgent({
        ...scrapeAgent,
        id: preview.agent?.id || scrapeAgent.id,
        name: preview.agent?.name || scrapeAgent.name,
      });
      setFlowPreview(preview);
      setFlowPreviewReadOnly(true);
      setScrapeApplyMessage('Preflight passed. No flow draft was saved.');
    } catch (err) {
      setFlowPreviewError(err.message || 'Generated draft preflight failed');
      setScrapeError(err.message || 'Generated draft preflight failed');
    } finally {
      setFlowPreviewLoading(false);
      setScrapePreflightLoading(false);
    }
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
                    <div className="d-flex gap-2">
                      {FLOW_VISUALIZATION_ENABLED && (
                        <button type="button" className="btn btn-outline-secondary btn-sm" onClick={() => openFlowPreview(agent)}>
                          Flow
                        </button>
                      )}
                      {SCRAPE_GENERATE_SCRIPT_ENABLED && user?.role === 'admin' && (
                        <button type="button" className="btn btn-outline-success btn-sm" onClick={() => openScrapeModal(agent)}>
                          Generate Script
                        </button>
                      )}
                      {user?.role === 'admin' && (
                        <button type="button" className="btn btn-outline-primary btn-sm" onClick={() => openEditModal(agent)}>
                          Edit
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {flowPreviewAgent && (
        <FlowPreviewModal
          agent={flowPreviewAgent}
          preview={flowPreview}
          loading={flowPreviewLoading}
          error={flowPreviewError}
          onClose={closeFlowPreview}
          onSave={!flowPreviewReadOnly && user?.role === 'admin' ? saveFlowDraft : null}
        />
      )}

      {scrapeAgent && (
        <div className="modal show d-block" tabIndex="-1" style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
          <div className="modal-dialog modal-lg modal-dialog-centered modal-dialog-scrollable">
            <div className="modal-content border-0 shadow">
              <div className="modal-header">
                <div>
                  <h5 className="modal-title fw-bold mb-1">Generate Script</h5>
                  <div className="text-muted small">{scrapeAgent.name || 'Voice Agent'}</div>
                </div>
                <button type="button" className="btn-close shadow-none" onClick={closeScrapeModal} disabled={scrapeLoading}></button>
              </div>
              <div className="modal-body bg-light">
                <form onSubmit={handleGenerateFromWebsite} className="border rounded bg-white p-3 mb-3">
                  <div className="row g-3 align-items-end">
                    <div className="col-md-8">
                      <label className="form-label small fw-bold">Website URL</label>
                      <input
                        type="url"
                        className="form-control"
                        required
                        value={scrapeUrl}
                        onChange={(event) => setScrapeUrl(event.target.value)}
                        placeholder="https://example.com"
                        disabled={scrapeLoading}
                      />
                    </div>
                    <div className="col-md-4">
                      <button type="submit" className="btn btn-success w-100" disabled={scrapeLoading || !scrapeUrl.trim()}>
                        {scrapeLoading ? 'Generating...' : 'Generate Draft'}
                      </button>
                    </div>
                  </div>
                </form>

                {scrapeError && <div className="alert alert-warning">{scrapeError}</div>}
                {scrapeApplyMessage && <div className="alert alert-success">{scrapeApplyMessage}</div>}

                <div className="row g-3 mb-3">
                  <div className="col-md-4">
                    <div className="border rounded bg-white p-3 h-100">
                      <div className="text-muted small">Job</div>
                      <div className="fw-bold text-capitalize">{scrapeJob?.status || 'Not started'}</div>
                    </div>
                  </div>
                  <div className="col-md-4">
                    <div className="border rounded bg-white p-3 h-100">
                      <div className="text-muted small">Worker</div>
                      <div className="fw-bold">{SCRAPE_WORKER_V1_ENABLED ? 'Queued' : 'Draft-only'}</div>
                    </div>
                  </div>
                  <div className="col-md-4">
                    <div className="border rounded bg-white p-3 h-100">
                      <div className="text-muted small">Status</div>
                      <div className="fw-bold">{scrapeStatus || 'Ready'}</div>
                    </div>
                  </div>
                </div>

                {scrapeDraft && (
                  <div className="border rounded bg-white p-3">
                    <div className="d-flex justify-content-between align-items-start gap-3 mb-3">
                      <div>
                        <div className="fw-bold">Generated Draft</div>
                        <div className="text-muted small">ID: {(scrapeDraft.id || '').substring(0, 8)}...</div>
                      </div>
                      <span className="badge bg-warning-subtle text-warning border border-warning-subtle">Review Required</span>
                    </div>
                    <div className="row g-3">
                      {draftQuality(scrapeDraft) && (
                        <div className="col-12">
                          <div className="d-flex align-items-center gap-2 flex-wrap">
                            <span className={`badge border text-capitalize ${qualityClass(draftQuality(scrapeDraft).level)}`}>
                              {draftQuality(scrapeDraft).level} readiness
                            </span>
                            <span className="small text-muted">Score {draftQuality(scrapeDraft).score}/100 - advisory only</span>
                          </div>
                        </div>
                      )}
                      <div className="col-md-6">
                        <div className="small text-muted">Business</div>
                        <div className="fw-semibold">{scrapeDraft.knowledge?.company?.name || scrapeDraft.knowledge?.domain || 'Unknown'}</div>
                      </div>
                      <div className="col-md-6">
                        <div className="small text-muted">Industry</div>
                        <div className="fw-semibold text-capitalize">{String(scrapeDraft.knowledge?.industry || 'unknown').replaceAll('_', ' ')}</div>
                      </div>
                      {contentInventoryItems(scrapeDraft.knowledge).length > 0 && (
                        <div className="col-12">
                          <div className="small text-muted mb-1">Content Inventory</div>
                          <div className="d-flex flex-wrap gap-1">
                            {contentInventoryItems(scrapeDraft.knowledge).map(([pageType, count]) => (
                              <span key={pageType} className="badge bg-light text-dark border text-capitalize">
                                {pageType.replaceAll('_', ' ')}: {count}
                              </span>
                            ))}
                            {scrapeDraft.knowledge?.content_inventory?.noise_filtered && (
                              <span className="badge bg-success-subtle text-success border border-success-subtle">Noise filtered</span>
                            )}
                          </div>
                        </div>
                      )}
                      <div className="col-md-6">
                        <div className="small text-muted mb-1">Services</div>
                        <div className="d-flex flex-wrap gap-1">
                          {(scrapeDraft.knowledge?.products_or_services || []).slice(0, 6).map((item, index) => (
                            <span key={`${item.name}-${index}`} className="badge bg-light text-dark border">{item.name}</span>
                          ))}
                          {!scrapeDraft.knowledge?.products_or_services?.length && <span className="text-muted small">None</span>}
                        </div>
                      </div>
                      <div className="col-md-6">
                        <div className="small text-muted mb-1">Draft Flow</div>
                        <div className="fw-semibold">
                          {scrapeDraft.draft?.nodes?.length || 0} nodes / {scrapeDraft.draft?.runtime_mode || 'shadow'}
                        </div>
                      </div>
                    </div>
                    {draftQuality(scrapeDraft)?.warnings?.length ? (
                      <div className="border-top mt-3 pt-3 small">
                        <div className="text-muted mb-1">Review warnings</div>
                        <ul className="mb-0 ps-3">
                          {draftQuality(scrapeDraft).warnings.slice(0, 4).map((warning, index) => (
                            <li key={`${warning}-${index}`}>{warning}</li>
                          ))}
                        </ul>
                      </div>
                    ) : null}
                    <ConversationGuidance knowledge={scrapeDraft.knowledge} />
                    {sourceEvidenceFromKnowledge(scrapeDraft.knowledge).length > 0 && (
                      <div className="border-top mt-3 pt-3 small">
                        <div className="text-muted mb-1">Source Evidence</div>
                        <div className="d-flex flex-column gap-1">
                          {sourceEvidenceFromKnowledge(scrapeDraft.knowledge).map((url) => (
                            <a key={url} href={url} target="_blank" rel="noreferrer" className="text-truncate">
                              {url}
                            </a>
                          ))}
                        </div>
                      </div>
                    )}
                    <div className="border-top mt-3 pt-3 d-flex justify-content-between align-items-center gap-3 flex-wrap">
                      <div className="small text-muted">
                        Applying saves a Flow V2 draft only. Live calls and published runtime stay unchanged.
                      </div>
                      <div className="d-flex gap-2">
                        <button
                          type="button"
                          className="btn btn-outline-secondary btn-sm"
                          onClick={() => handlePreflightGeneratedDraft()}
                          disabled={scrapePreflightLoading || scrapeApplyLoading || scrapeLoading || !FLOW_VISUALIZATION_ENABLED}
                        >
                          {scrapePreflightLoading ? 'Checking...' : 'Preflight'}
                        </button>
                        <button
                          type="button"
                          className="btn btn-outline-primary btn-sm"
                          onClick={() => handleApplyGeneratedDraft()}
                          disabled={scrapeApplyLoading || scrapePreflightLoading || scrapeLoading || !FLOW_VISUALIZATION_ENABLED}
                        >
                          {scrapeApplyLoading ? 'Saving Draft...' : 'Save to Flow Draft'}
                        </button>
                      </div>
                    </div>
                    {!FLOW_VISUALIZATION_ENABLED && (
                      <div className="small text-muted mt-2">Enable flow visualization to review this draft in the flow editor.</div>
                    )}
                  </div>
                )}

                <div className="border rounded bg-white p-3 mt-3">
                  <div className="d-flex justify-content-between align-items-center mb-3">
                    <div>
                      <div className="fw-bold">Previous Drafts</div>
                      <div className="text-muted small">Generated website drafts for this agent.</div>
                    </div>
                    <button
                      type="button"
                      className="btn btn-light border btn-sm"
                      onClick={() => loadScrapeDraftHistory(scrapeAgent)}
                      disabled={scrapeHistoryLoading || scrapeLoading}
                    >
                      {scrapeHistoryLoading ? 'Loading...' : 'Refresh'}
                    </button>
                  </div>
                  {scrapeHistoryLoading ? (
                    <div className="text-muted small">Loading drafts...</div>
                  ) : scrapeDraftHistory.length === 0 ? (
                    <div className="text-muted small">No previous generated drafts for this agent.</div>
                  ) : (
                    <div className="d-flex flex-column gap-2">
                      {scrapeDraftHistory.map((draft) => (
                        <div key={draft.id} className="border rounded p-2 d-flex justify-content-between align-items-center gap-3">
                          <div className="small">
                            <div className="fw-semibold">{draft.knowledge?.company?.name || draft.knowledge?.domain || 'Website Draft'}</div>
                            <div className="text-muted">
                              {String(draft.knowledge?.industry || 'unknown').replaceAll('_', ' ')}
                              {' '} - {(draft.id || '').substring(0, 8)} - {draft.status || 'draft'}
                            </div>
                            {draftQuality(draft) && (
                              <div className="mt-1">
                                <span className={`badge border text-capitalize ${qualityClass(draftQuality(draft).level)}`}>
                                  {draftQuality(draft).level} readiness
                                </span>
                              </div>
                            )}
                            {draft.reviewed_at && (
                              <div className="text-success mt-1">Saved to Flow Draft {new Date(draft.reviewed_at).toLocaleString()}</div>
                            )}
                          </div>
                          <div className="d-flex gap-2">
                            <button
                              type="button"
                              className="btn btn-outline-secondary btn-sm"
                              onClick={() => handlePreflightGeneratedDraft(draft)}
                              disabled={scrapePreflightLoading || scrapeApplyLoading || scrapeLoading || !FLOW_VISUALIZATION_ENABLED}
                            >
                              {scrapePreflightLoading ? 'Checking...' : 'Preflight'}
                            </button>
                            <button
                              type="button"
                              className="btn btn-outline-primary btn-sm"
                              onClick={() => handleApplyGeneratedDraft(draft)}
                              disabled={scrapeApplyLoading || scrapePreflightLoading || scrapeLoading || !FLOW_VISUALIZATION_ENABLED}
                            >
                              Apply
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-light border" onClick={closeScrapeModal} disabled={scrapeLoading}>Close</button>
              </div>
            </div>
          </div>
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
