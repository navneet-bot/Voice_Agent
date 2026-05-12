"""
Voice AI Calling SaaS Platform — Main Server  v2.1 (Production Hardened)

Changes from v2.0:
  - lifespan replaces deprecated on_event
  - websocket.accept() now called BEFORE pipeline starts (Issue 2)
  - API Key middleware — X-API-Key header guards all write endpoints (Issue 6)
  - VoiceLiveSink emits speaker labels in transcript events (Issue 9)
  - agentId resolved from DB assignment on /api/assignments (Issue 3)
  - /health endpoint for uptime monitoring (Issue 14)
  - /api/voice-demo  — mic session that also fires dashboard WS events (Issue 12)
  - Groq 429 retry with exponential backoff in generate_response (Issue 13)
"""

from __future__ import annotations

# ── Fix #4: Force UTF-8 on Windows stdout/stderr ─────────────────────────────
# Python on Windows uses the active console code page (usually cp1252) which
# cannot encode Devanagari, Unicode arrows (→), or emoji. This causes
# UnicodeEncodeError in the logging StreamHandler, silently swallowing log lines.
# Reconfigure BEFORE any import that might trigger logging.
import sys
import io as _io
import time

def _force_utf8_streams() -> None:
    for _stream_name in ("stdout", "stderr"):
        _stream = getattr(sys, _stream_name, None)
        if _stream and hasattr(_stream, "buffer"):
            setattr(
                sys,
                _stream_name,
                _io.TextIOWrapper(_stream.buffer, encoding="utf-8", errors="replace", line_buffering=True),
            )

_force_utf8_streams()
# ─────────────────────────────────────────────────────────────────────────────

import asyncio
import json
import logging
import os
import secrets
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

# ── Internal modules ──────────────────────────────────────────────────────────
from ws_hub import ws_manager
from db.db_manager import db
from demo_runner import DemoCallEngine
from agent_runner import run_campaign
from telephony.provider_registry import get_provider, list_providers
from metrics.provider_metrics import snapshot_provider_metrics
from call_recording import SessionRecorder as TimelineSessionRecorder

_PIPECAT_AVAILABLE = False
try:
    from pipecat.frames.frames import AudioRawFrame, CancelFrame, EndFrame, Frame, StartFrame, TextFrame
    from pipecat.pipeline.pipeline import Pipeline
    from pipecat.pipeline.runner import PipelineRunner
    from pipecat.pipeline.task import PipelineTask
    from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
    from flows.runtime import AgentTextFrame, RealEstateSTTProcessor, RealEstateLLMProcessor, RealEstateTTSProcessor, VoiceTurnState
    _PIPECAT_AVAILABLE = True
except (ImportError, Exception) as e:
    import logging
    logging.getLogger("server").warning(f"Skipping pipecat/flows imports: {e}")
    class FrameProcessor: pass  # type: ignore[no-redef]

from llm.state_manager import StateManager

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s",
    handlers=[
        logging.FileHandler("voice_agent.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("server")

# ── Constants ─────────────────────────────────────────────────────────────────
DB_DIR           = "db"
AGENTS_DIR       = os.path.join(DB_DIR, "agents")
os.makedirs(DB_DIR, exist_ok=True)
os.makedirs(AGENTS_DIR, exist_ok=True)
WEBHOOK_BASE_URL = os.getenv("WEBHOOK_BASE_URL", "http://localhost:3000")
DEFAULT_CARTESIA_VOICE_ID = "95d51f79-c397-46f9-b49a-23763d3eaa2d"
VALID_STT_PROVIDERS = {"groq", "deepgram"}
VALID_TTS_PROVIDERS = {"edge", "cartesia"}
VALID_AGENT_TYPES = {"real_estate_sales", "finance", "insurance", "education"}
AGENT_TYPE_LABELS = {
    "real_estate_sales": "Real Estate team",
    "finance": "Finance advisory team",
    "insurance": "Insurance advisory team",
    "education": "Education counselling team",
}
VOICE_MAP = {"ElevenLabs - Priya (Female)": "11labs-06nek6zjTCD1vCbtc8bc"}

# API Key Auth — set PLATFORM_API_KEY in .env; if empty, auth is DISABLED (dev mode)
_PLATFORM_API_KEY = os.getenv("PLATFORM_API_KEY", "")
_api_key_header   = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_auth(key: Optional[str] = Depends(_api_key_header)) -> None:
    """Dependency: validates X-API-Key header on write endpoints.
    If PLATFORM_API_KEY is not set in .env, auth is skipped (development mode).
    """
    if not _PLATFORM_API_KEY:
        return  # dev mode — no key required
    if key != _PLATFORM_API_KEY:
        raise HTTPException(status_code=403, detail="Forbidden: invalid or missing API key")


# ── App lifespan (replaces deprecated on_event) ───────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: initialize DB and migrate JSON files. Shutdown: nothing needed."""
    logger.info("Initializing database...")
    await db.initialize()
    logger.info("Database ready.")
    yield
    logger.info("Server shutting down.")


# ── App setup ─────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Voice AI Calling SaaS Platform",
    version="2.1",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("recordings", exist_ok=True)
app.mount("/recordings", StaticFiles(directory="recordings"), name="recordings")


# ── Pydantic Models ───────────────────────────────────────────────────────────
class AgentCreate(BaseModel):
    name: str
    voice: str
    language: str
    max_duration: int
    provider: str
    stt_provider: str = "groq"
    tts_provider: str = "edge"
    cartesia_voice_id: Optional[str] = None
    assigned_email: Optional[str] = None
    agent_type: str = "real_estate_sales"
    script: str
    data_fields: List[str]

class AgentUpdate(BaseModel):
    name: Optional[str] = None
    voice: Optional[str] = None
    language: Optional[str] = None
    max_duration: Optional[int] = None
    provider: Optional[str] = None
    stt_provider: Optional[str] = None
    tts_provider: Optional[str] = None
    cartesia_voice_id: Optional[str] = None
    assigned_email: Optional[str] = None
    agent_type: Optional[str] = None
    script: Optional[str] = None
    data_fields: Optional[List[str]] = None

class LeadsUpload(BaseModel):
    campaignId: str
    leads: List[dict]

class CampaignCreate(BaseModel):
    campaignId: str
    agentId: Optional[str] = None
    telephonyProvider: Optional[str] = "demo"

class CampaignStart(BaseModel):
    campaignId: str
    agentId: Optional[str] = None
    telephonyProvider: Optional[str] = "demo"

class AssignmentUpdate(BaseModel):
    clientId: str
    agentId: str

class DemoStart(BaseModel):
    campaignId: str
    agentId: Optional[str] = None
    leadOverride: Optional[dict] = None
    clientId: Optional[str] = "global"

class PhoneNumberPurchase(BaseModel):
    phoneNumber: str
    provider: str = "twilio"
    clientId: Optional[str] = None

class PhoneNumberAssign(BaseModel):
    numberId: str
    clientId: str

class ClientCreate(BaseModel):
    id: str
    name: str
    email: Optional[str] = None
    plan: Optional[str] = "free"
    agentName: Optional[str] = None
    agentId: Optional[str] = None


# ── Health Check ──────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    """
    Uptime monitoring endpoint. UptimeRobot / BetterUptime hits this every 5 min.
    Returns 200 if server is alive and DB is reachable.
    """
    try:
        await db.get_dashboard_stats()
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {e}"

    return {
        "status": "ok",
        "version": "2.1",
        "db": db_status,
        "auth": "enabled" if _PLATFORM_API_KEY else "disabled (dev mode)",
        "timestamp": datetime.now().isoformat(),
    }


# ── Frontend / Health ─────────────────────────────────────────────────────────
@app.get("/")
def health():
    return {"status": "ok"}

@app.get("/audio-worklet-processor.js")
async def serve_audio_worklet():
    """Serve the AudioWorklet processor script (replaces deprecated ScriptProcessor)."""
    worklet_path = os.path.join(os.path.dirname(__file__), "..", "Frontend", "audio-worklet-processor.js")
    if os.path.exists(worklet_path):
        return FileResponse(worklet_path, media_type="application/javascript")
    # Inline fallback if file doesn't exist yet
    js = """
class MicCaptureProcessor extends AudioWorkletProcessor {
  constructor() { super(); this._buffer = []; }
  process(inputs) {
    const ch = inputs[0]?.[0];
    if (ch) { for (let i = 0; i < ch.length; i++) this._buffer.push(ch[i]); }
    if (this._buffer.length >= 2048) {
      this.port.postMessage(new Float32Array(this._buffer.splice(0, 2048)));
    }
    return true;
  }
}
registerProcessor('mic-capture-processor', MicCaptureProcessor);
"""
    return HTMLResponse(js, media_type="application/javascript")


# ── Dashboard Stats ───────────────────────────────────────────────────────────
@app.get("/api/dashboard")
async def get_dashboard():
    return await db.get_dashboard_stats()

@app.get("/api/provider-metrics")
async def get_provider_metrics():
    return snapshot_provider_metrics()

def _voice_id_for_agent(voice: str | None) -> str:
    raw_voice = (voice or "11labs-06nek6zjTCD1vCbtc8bc").strip()
    return VOICE_MAP.get(raw_voice, raw_voice)


def _clean_agent_data_fields(fields: Any) -> list[str]:
    if isinstance(fields, str):
        return [item.strip() for item in fields.split(",") if item.strip()]
    if isinstance(fields, list):
        return [str(item).strip() for item in fields if str(item).strip()]
    return []


def _normalize_agent_record(data: dict) -> dict:
    normalized = dict(data)
    normalized["name"] = str(normalized.get("name") or "Voice Agent").strip()
    normalized["voice"] = str(normalized.get("voice") or "11labs-06nek6zjTCD1vCbtc8bc").strip()
    normalized["language"] = str(normalized.get("language") or "English").strip()
    normalized["max_duration"] = int(normalized.get("max_duration") or 300)
    normalized["provider"] = str(normalized.get("provider") or "twilio").strip()
    stt_provider = str(normalized.get("stt_provider") or "groq").strip().lower()
    tts_provider = str(normalized.get("tts_provider") or "edge").strip().lower()
    normalized["stt_provider"] = stt_provider if stt_provider in VALID_STT_PROVIDERS else "groq"
    normalized["tts_provider"] = tts_provider if tts_provider in VALID_TTS_PROVIDERS else "edge"
    normalized["cartesia_voice_id"] = str(normalized.get("cartesia_voice_id") or DEFAULT_CARTESIA_VOICE_ID).strip()
    normalized["assigned_email"] = str(normalized.get("assigned_email") or "").strip().lower()
    agent_type = str(normalized.get("agent_type") or "real_estate_sales").strip()
    normalized["agent_type"] = agent_type if agent_type in VALID_AGENT_TYPES else "real_estate_sales"
    normalized["script"] = str(normalized.get("script") or "").strip()
    normalized["data_fields"] = _clean_agent_data_fields(normalized.get("data_fields"))
    return normalized


def _agent_schema_path(agent_id: str, existing_path: str | None = None) -> str:
    expected_path = os.path.join(AGENTS_DIR, f"{agent_id}.json")
    if not existing_path:
        return expected_path

    root = os.path.abspath(AGENTS_DIR)
    candidate = os.path.abspath(existing_path)
    if candidate == os.path.abspath(expected_path) or candidate.startswith(root + os.sep):
        return existing_path
    logger.warning("Ignoring unsafe schema_path for agent_id=%s: %s", agent_id, existing_path)
    return expected_path


def _write_agent_runtime_schema(
    agent_id: str,
    schema_path: str,
    agent_data: dict,
    voice_id: str,
    assigned_client: Optional[dict],
) -> None:
    try:
        with open(schema_path, "r", encoding="utf-8") as existing_file:
            schema = json.load(existing_file)
    except (OSError, json.JSONDecodeError):
        schema = StateManager.template_new_agent(
            name=agent_data["name"],
            script=agent_data["script"],
            voice_id=voice_id,
            data_fields=agent_data["data_fields"],
            agent_type=agent_data["agent_type"],
        )

    if not isinstance(schema, dict):
        schema = {}

    type_label = AGENT_TYPE_LABELS.get(agent_data["agent_type"], "Customer advisory team")
    schema["agent_name"] = agent_data["name"]
    schema["voice_id"] = voice_id
    schema["global_prompt"] = agent_data["script"]
    schema["provider_config"] = {
        "stt_provider": agent_data["stt_provider"],
        "tts_provider": agent_data["tts_provider"],
        "cartesia_voice_id": agent_data["cartesia_voice_id"],
    }
    schema["agent_metadata"] = {
        "agent_type": agent_data["agent_type"],
        "assigned_email": agent_data["assigned_email"],
        "client_id": assigned_client.get("id") if assigned_client else None,
    }

    flow = schema.get("conversationFlow")
    if not isinstance(flow, dict):
        flow = {"start_node_id": "root_greeting", "nodes": []}
        schema["conversationFlow"] = flow
    flow["global_prompt"] = agent_data["script"]
    flow.setdefault("start_node_id", "root_greeting")

    nodes = flow.get("nodes")
    if not isinstance(nodes, list):
        nodes = []
        flow["nodes"] = nodes

    root = next((node for node in nodes if node.get("id") == "root_greeting"), None)
    if not root:
        root = {
            "id": "root_greeting",
            "name": "Initial Greeting",
            "type": "conversation",
            "intent_triggers": ["call_connected"],
            "edges": [{"id": "to_discovery", "condition": "user responds", "destination_node_id": "discovery"}],
        }
        nodes.insert(0, root)
    root["instruction"] = {
        "type": "prompt",
        "text": f"Greet the user warmly as {agent_data['name']} and confirm identity using the lead name.",
    }
    root["response"] = f"Hello, this is {agent_data['name']} from the {type_label}. Am I speaking with {{{{name}}}}?"

    for node in nodes:
        if node.get("id") == "discovery":
            node["collects"] = agent_data["data_fields"]

    os.makedirs(os.path.dirname(schema_path), exist_ok=True)
    with open(schema_path, "w", encoding="utf-8") as schema_file:
        json.dump(schema, schema_file, indent=4)


# ── Agents ────────────────────────────────────────────────────────────────────
@app.get("/api/agents")
async def list_agents(client_id: Optional[str] = None, user_email: Optional[str] = None):
    if user_email:
        client = await db.get_client_by_email(user_email)
        if not client:
            return []
        return await db.list_agents(client["id"])
    return await db.list_agents(client_id)

@app.get("/api/clients/resolve")
async def resolve_client_by_email(email: str):
    client = await db.get_client_by_email(email)
    if not client:
        return {"client": None, "assignment": None, "agents": []}

    agents = await db.list_agents(client["id"])
    assigned_agent_id = await db.get_assignment(client["id"])
    assigned_agent = next((agent for agent in agents if agent.get("id") == assigned_agent_id), None)
    return {
        "client": client,
        "assignment": {
            "agentId": assigned_agent_id,
            "agent": assigned_agent,
        } if assigned_agent_id else None,
        "agents": agents,
    }

@app.post("/api/agents", dependencies=[Depends(require_auth)])
async def create_agent(agent: AgentCreate):
    agent_id = str(uuid.uuid4())
    data = _normalize_agent_record(agent.dict())
    voice_id = _voice_id_for_agent(data["voice"])
    assigned_email = data["assigned_email"]
    assigned_client = None
    if assigned_email:
        assigned_client = await db.ensure_client_for_email(assigned_email)

    schema_path = os.path.join(AGENTS_DIR, f"{agent_id}.json")
    _write_agent_runtime_schema(agent_id, schema_path, data, voice_id, assigned_client)
    data.update({
        "client_id": assigned_client.get("id") if assigned_client else None,
        "schema_path": schema_path,
        "created_at": datetime.now().isoformat(),
    })
    created = await db.create_agent(agent_id, data)
    if assigned_client:
        await db.set_assignment(assigned_client["id"], agent_id)
    return created


@app.put("/api/agents/{agent_id}", dependencies=[Depends(require_auth)])
async def update_agent(agent_id: str, agent: AgentUpdate):
    existing = await db.get_agent(agent_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Agent not found")

    patch = agent.dict(exclude_unset=True)
    merged = _normalize_agent_record({**existing, **patch})
    voice_id = _voice_id_for_agent(merged["voice"])
    previous_client_id = existing.get("client_id")

    assigned_client = None
    if merged["assigned_email"]:
        assigned_client = await db.ensure_client_for_email(merged["assigned_email"])

    schema_path = _agent_schema_path(agent_id, existing.get("schema_path"))
    _write_agent_runtime_schema(agent_id, schema_path, merged, voice_id, assigned_client)
    merged.update({
        "client_id": assigned_client.get("id") if assigned_client else None,
        "schema_path": schema_path,
    })

    updated = await db.update_agent(agent_id, merged)
    if not updated:
        raise HTTPException(status_code=404, detail="Agent not found")

    new_client_id = assigned_client.get("id") if assigned_client else None
    if previous_client_id and previous_client_id != new_client_id:
        await db.clear_assignment(previous_client_id, agent_id)
    if new_client_id:
        await db.set_assignment(new_client_id, agent_id)

    return updated


# Agent editing intentionally updates DB metadata and runtime JSON schema together.
@app.post("/api/leads/upload", dependencies=[Depends(require_auth)])
async def upload_leads(data: LeadsUpload):
    await db.upsert_leads(data.campaignId, data.leads)
    existing = await db.get_campaign(data.campaignId)
    if not existing:
        await db.upsert_campaign(data.campaignId, {"status": "Pending", "created_at": datetime.now().isoformat()})
    else:
        await db.set_campaign_status(data.campaignId, "Pending")
    return {"status": "success", "count": len(data.leads)}


# ── Campaigns ─────────────────────────────────────────────────────────────────
@app.get("/api/campaigns")
async def list_campaigns():
    return await db.list_campaigns()

@app.post("/api/campaigns/start", dependencies=[Depends(require_auth)])
async def start_campaign(data: CampaignStart, background_tasks: BackgroundTasks):
    campaign = await db.get_campaign(data.campaignId)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    await db.set_campaign_status(data.campaignId, "Active")
    provider_slug     = data.telephonyProvider or "demo"
    agent_id          = data.agentId or "default"
    if provider_slug == "demo":
        engine           = DemoCallEngine(ws_manager=ws_manager, db=db)
        agent_schema_path = _resolve_schema(agent_id)
        background_tasks.add_task(engine.run_demo_campaign, data.campaignId, agent_schema_path)
    else:
        background_tasks.add_task(run_campaign, data.campaignId, agent_id, provider_slug)
    return {"status": "started", "provider": provider_slug}

@app.get("/api/campaigns/{campaign_id}/results")
async def get_results(campaign_id: str):
    return await db.get_results_for_campaign(campaign_id)

@app.get("/api/results/{lead_id}/transcript")
async def get_transcript(lead_id: str):
    return await db.get_transcript_for_lead(lead_id)

@app.get("/api/campaigns/{campaign_id}/live")
async def get_live_state(campaign_id: str):
    return await db.get_live_state(campaign_id)

@app.get("/api/campaigns/all/live")
async def get_all_live_state():
    return await db.get_all_live_state()


# ── Demo Mode (simulated calls — AI vs AI) ────────────────────────────────────
@app.post("/api/demo/start", dependencies=[Depends(require_auth)])
async def start_demo(data: DemoStart, background_tasks: BackgroundTasks):
    """
    Start a simulated demo campaign (AI generates human responses).
    Dashboard updates in real-time via WebSocket.
    """
    campaign_id       = data.campaignId
    agent_id          = data.agentId or "default"
    agent_schema_path = _resolve_schema(agent_id)
    client_id         = data.clientId or "global"

    existing = await db.get_campaign(campaign_id)
    if not existing:
        await db.upsert_campaign(campaign_id, {
            "status": "Active",
            "telephony_provider": "demo",
            "client_id": client_id,
            "created_at": datetime.now().isoformat(),
        })
    else:
        await db.set_campaign_status(campaign_id, "Active")

    engine = DemoCallEngine(ws_manager=ws_manager, db=db)
    if data.leadOverride:
        background_tasks.add_task(engine.run_demo_call, campaign_id, data.leadOverride, agent_schema_path, client_id)
    else:
        background_tasks.add_task(engine.run_demo_campaign, campaign_id, agent_schema_path, client_id)

    return {"status": "demo_started", "campaign_id": campaign_id}


# ── Clients ───────────────────────────────────────────────────────────────────
@app.get("/api/clients")
async def list_clients():
    return await db.list_clients()

@app.post("/api/clients", dependencies=[Depends(require_auth)])
async def create_client(client: ClientCreate):
    client_data = client.dict()
    # If agent info is provided, also set the assignment
    result = await db.create_client(client.id, client_data)
    if client.agentId:
        await db.set_assignment(client.id, client.agentId)
    return result


# ── Assignments ───────────────────────────────────────────────────────────────
@app.get("/api/assignments/{client_id}")
async def get_assignment(client_id: str):
    agent_id = await db.get_assignment(client_id)
    if not agent_id:
        return {"agentId": None}
    agents = await db.list_agents()
    agent  = next((a for a in agents if a["id"] == agent_id), None)
    return {"agentId": agent_id, "agent": agent}

@app.post("/api/assignments", dependencies=[Depends(require_auth)])
async def update_assignment(data: AssignmentUpdate):
    await db.set_assignment(data.clientId, data.agentId)
    return {"status": "success"}


# ── Telephony Providers ───────────────────────────────────────────────────────
@app.get("/api/telephony/providers")
async def get_providers():
    return list_providers()

@app.get("/api/telephony/numbers")
async def list_numbers(client_id: Optional[str] = None):
    return await db.list_phone_numbers(client_id)

@app.post("/api/telephony/numbers/search")
async def search_numbers(provider: str = "twilio", country_code: str = "IN"):
    p = get_provider(provider)
    return await p.list_available_numbers(country_code)

@app.post("/api/telephony/numbers/purchase", dependencies=[Depends(require_auth)])
async def purchase_number(data: PhoneNumberPurchase):
    provider = get_provider(data.provider)
    result   = await provider.purchase_number(data.phoneNumber)
    if result.get("status") in ("active", "simulated"):
        number_data = {
            "phone":     result["phone"],
            "sid":       result.get("sid", ""),
            "provider":  data.provider,
            "client_id": data.clientId,
            "region":    "",
        }
        saved = await db.add_phone_number(number_data)
        return {"status": "success", **saved}
    raise HTTPException(status_code=400, detail=result.get("error", "Purchase failed"))

@app.post("/api/telephony/numbers/assign", dependencies=[Depends(require_auth)])
async def assign_number(data: PhoneNumberAssign):
    await db.assign_number_to_client(data.numberId, data.clientId)
    return {"status": "success"}

@app.post("/api/telephony/buy")  # legacy compat
async def legacy_buy_number():
    return {"status": "success", "phone": "+91 9122 " + str(uuid.uuid4().int)[:6]}


# ── Twilio Webhooks ───────────────────────────────────────────────────────────
@app.post("/telephony/twiml/{call_id}")
async def twilio_twiml(call_id: str, request: Request):
    from telephony.twilio_handler import build_twiml
    ws_url     = WEBHOOK_BASE_URL.replace("http://", "wss://").replace("https://", "wss://")
    stream_url = f"{ws_url}/telephony/stream/{call_id}"
    twiml      = build_twiml(stream_url)
    return HTMLResponse(content=twiml, media_type="application/xml")

@app.websocket("/telephony/stream/{call_id}")
async def twilio_stream(websocket: WebSocket, call_id: str):
    from telephony.twilio_handler import handle_twilio_stream
    from ws_hub import call_registry

    # Resolve per-call context registered by agent_runner.run_campaign()
    # Falls back gracefully for inbound/unknown calls.
    meta = call_registry.get(call_id) or {}
    agent_schema_path = meta.get("agent_schema_path") or _resolve_schema("default")

    try:
        await handle_twilio_stream(
            websocket,
            call_id=call_id,
            agent_schema_path=agent_schema_path,
            ws_manager=ws_manager,
            db=db,
            campaign_id=meta.get("campaign_id", ""),
            lead_id=call_id,
            lead_name=meta.get("lead_name", "Lead"),
            phone=meta.get("phone", ""),
            client_id=meta.get("client_id", "global"),
        )
    finally:
        # Always clean up the registry entry even if the handler raises
        call_registry.clear(call_id)


# ── WebSocket Dashboard Hub ───────────────────────────────────────────────────
@app.websocket("/ws/dashboard/{client_id}")
async def dashboard_ws(websocket: WebSocket, client_id: str = "global"):
    await ws_manager.connect(websocket, client_id)
    logger.info("Dashboard WS connected: client=%s", client_id)
    try:
        while True:
            msg = await websocket.receive()
            if msg["type"] == "websocket.receive":
                # handle ping frames from frontend by replying with pong
                text_data = msg.get("text")
                if text_data == "ping":
                    try:
                        await websocket.send_text("pong")
                    except Exception:
                        pass
            elif msg["type"] == "websocket.disconnect":
                break
    except WebSocketDisconnect:
        logger.info("Dashboard WS disconnected: client=%s", client_id)
    except Exception as e:
        logger.error("Dashboard WS error: %s", e)
    finally:
        await ws_manager.disconnect(websocket, client_id)

@app.websocket("/ws/dashboard")
async def dashboard_ws_global(websocket: WebSocket):
    await dashboard_ws(websocket, client_id="global")


# ── VoiceLiveSource / VoiceLiveSink (shared by /api/voice-live and /api/voice-demo) ──


import time

class SessionRecorder(TimelineSessionRecorder):
    """Compatibility alias for the timeline-aware recorder."""
    pass

class VoiceLiveSource(FrameProcessor):
    """Bridges browser mic audio into the Pipecat pipeline with backpressure."""

    def __init__(self, recorder=None):
        super().__init__()
        self.recorder = recorder
        self._started = False
        self._terminated = False
        self._sample_rate = 16000 # Default fallback
        # Keep a little extra headroom so short browser/network jitter does not drop speech.
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=32)
        self._process_task = None
        self._frames_received = 0
        self._frames_dropped = 0
        self._stats_started_at = time.monotonic()
        self._last_stats_log_at = 0.0

    def set_sample_rate(self, rate: int):
        self._sample_rate = rate
        logger.info("VoiceLiveSource: Input sample rate set to %d", rate)

    async def _process_queue(self):
        while not self._started:
            await asyncio.sleep(0.05)
        while not self._terminated:
            try:
                frame = await self._queue.get()
                await self.push_frame(frame, FrameDirection.DOWNSTREAM)
                self._queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("VoiceLiveSource queue error: %s", e)

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        """Hard Session State Machine enforcement."""
        await super().process_frame(frame, direction)
        
        if isinstance(frame, StartFrame):
            self._started = True
            logger.info("Session started handshake received.")
            if not self._process_task:
                self._process_task = asyncio.create_task(self._process_queue())
        
        if isinstance(frame, EndFrame):
            self._terminated = True
            logger.info("Session terminated.")

        await self.push_frame(frame, direction)

    def queue_audio(self, data: bytes):
        """Intelligent Selective Backpressure (Senior Requirement)."""
        if self._terminated:
            return
        if not data:
            return
            
        # Use the dynamically detected sample rate from the client
        frame = AudioRawFrame(audio=data, sample_rate=self._sample_rate, num_channels=1)
        _ensure_frame_attrs(frame)
        self._frames_received += 1
        now = time.monotonic()
        if (now - self._last_stats_log_at) >= 1.0:
            queue_depth = self._queue.qsize()
            frame_ms = (len(data) / 2 / max(self._sample_rate, 1)) * 1000.0
            logger.info(
                "VoiceLiveSource: frame_bytes=%d frame_ms=%.1f queue=%d/%d dropped=%d received=%d sample_rate=%d",
                len(data),
                frame_ms,
                queue_depth,
                self._queue.maxsize,
                self._frames_dropped,
                self._frames_received,
                self._sample_rate,
            )
            self._last_stats_log_at = now
        
        try:
            self._queue.put_nowait(frame)
            if self.recorder:
                self.recorder.add_user_audio(data, sample_rate=self._sample_rate)
        except asyncio.QueueFull:
            try:
                dropped = self._queue.get_nowait()
                if isinstance(dropped, (StartFrame, EndFrame)):
                    self._queue.put_nowait(dropped)
                    return 
                self._frames_dropped += 1
                self._queue.put_nowait(frame)
            except Exception:
                pass


def _ensure_frame_attrs(frame: Frame) -> None:
    try:
        if not hasattr(frame, "id") or getattr(frame, "id", None) is None:
            frame.id = f"ws_{uuid.uuid4().hex[:12]}"
    except Exception:
        pass
    try:
        if not hasattr(frame, "broadcast_sibling_id"):
            frame.broadcast_sibling_id = None
    except Exception:
        pass


class VoiceLiveSink(FrameProcessor):
    """Sends pipeline output back to the browser WebSocket."""

    def __init__(self, websocket: WebSocket, on_transcript=None, recorder=None):
        super().__init__()
        self.ws = websocket
        self.on_transcript = on_transcript
        self.recorder = recorder

    async def process_frame(self, frame, direction):
        frame_type = type(frame).__name__
        if isinstance(frame, CancelFrame):
            logger.info("[PIPELINE] SINK <- CancelFrame")
            try:
                await self.ws.send_text(json.dumps({"type": "cancel"}))
            except Exception as e:
                logger.error("[PIPELINE] SINK -> Failed sending cancel payload: %s", e)
            await self.push_frame(frame, direction)
            return

        try:
            await super().process_frame(frame, direction)
        except BaseException as exc:
            logger.error("[PIPELINE] SINK -> super().process_frame failed for type=%s: %s", frame_type, exc)
            if not isinstance(frame, (AudioRawFrame, TextFrame)):
                return

        if isinstance(frame, AudioRawFrame):
            print("SINK RECEIVED AUDIO")
            logger.info(
                "[PIPELINE] SINK <- AudioRawFrame bytes=%d",
                len(frame.audio),
            )
            try:
                # Send raw PCM16 audio bytes directly to the browser.
                await self.ws.send_bytes(frame.audio)
                if self.recorder:
                    self.recorder.add_agent_audio(frame.audio, sample_rate=frame.sample_rate)
                logger.info(
                    "[PIPELINE] SINK -> Sent audio bytes=%d",
                    len(frame.audio),
                )
            except Exception as exc:
                logger.error("[PIPELINE] SINK -> Failed sending audio: %s", exc)

        elif isinstance(frame, TextFrame):
            is_agent = isinstance(frame, AgentTextFrame)
            speaker  = "agent" if is_agent else "user"
            try:
                payload = {
                    "type":    "transcript",
                    "speaker": speaker,
                    "text":    frame.text,
                }
                await self.ws.send_text(json.dumps(payload))
            except Exception as exc:
                logger.error("[PIPELINE] SINK -> Failed sending transcript payload: %s", exc)
            
            if self.on_transcript:
                try:
                    await self.on_transcript(speaker, frame.text)
                except Exception as exc:
                    logger.error("[PIPELINE] SINK -> on_transcript callback failed: %s", exc)

        await self.push_frame(frame, direction)


# ── Live Voice — plain voice chat (no dashboard events) ──────────────────────
@app.websocket("/api/voice-live")
async def websocket_voice_live(websocket: WebSocket):
    """
    Simple browser mic → STT → LLM → TTS → browser speakers.
    No dashboard events. Used by the Talk Live page.
    Fix Issue 2: websocket.accept() is now called FIRST.
    """
    # Accept BEFORE touching anything else
    await websocket.accept()

    agent_id    = websocket.query_params.get("agentId", "default")
    lead_name   = websocket.query_params.get("leadName", "Prashant")
    schema_path = _resolve_schema(agent_id)
    logger.info("Live Voice: Connected — agent=%s schema=%s", agent_id, schema_path)

    source = VoiceLiveSource()
    turn_state = VoiceTurnState()
    stt    = RealEstateSTTProcessor(turn_state=turn_state, agent_id=agent_id)
    llm    = RealEstateLLMProcessor()
    llm.state_manager = StateManager(schema_path)
    llm.state_manager.conversation_data["name"] = lead_name
    llm.state_manager.conversation_data["lead_name"] = lead_name
    tts    = RealEstateTTSProcessor(turn_state=turn_state, agent_id=agent_id)
    sink   = VoiceLiveSink(websocket)

    pipeline    = Pipeline([source, stt, llm, tts, sink])
    runner      = PipelineRunner()
    task        = PipelineTask(pipeline)
    runner_task = asyncio.create_task(runner.run(task))

    async def reader():
        try:
            while True:
                msg = await websocket.receive()
                if msg["type"] == "websocket.receive":
                    text = msg.get("text")
                    if text:
                        try:
                            # Handle dynamic sample rate handshake
                            payload = json.loads(text)
                            if payload.get("type") == "mic_ready":
                                source.set_sample_rate(payload.get("sampleRate", 16000))
                        except Exception:
                            pass
                        continue

                    data = msg.get("bytes") or b""
                    if data:
                        if data == b"ping":
                            try: await websocket.send_bytes(b"pong")
                            except Exception: pass
                            continue
                        source.queue_audio(data)
                elif msg["type"] == "websocket.disconnect":
                    break
        except WebSocketDisconnect:
            pass
        except Exception as e:
            logger.error("Live Voice Reader Task Error: %s", e)

    try:
        await reader()
    finally:
        try:
            if source._process_task:
                source._process_task.cancel()
            await source.process_frame(EndFrame(), FrameDirection.DOWNSTREAM)
            await asyncio.sleep(0.3)
            runner_task.cancel()
            await runner_task
        except (asyncio.CancelledError, Exception):
            pass


# ── Voice Demo — browser mic + live dashboard events  ────────────────────────
@app.websocket("/api/voice-demo")
async def websocket_voice_demo(websocket: WebSocket):
    """
    Client speaks via browser mic. The AI pipeline runs normally.
    ADDITIONALLY: every transcript exchange fires dashboard WebSocket events
    so the Live Feed panel shows ringing → talking → transcript → completed,
    exactly the same as a real campaign call.

    Query params:
      agentId    — which agent schema to use
      clientId   — for WS broadcast scoping (defaults to 'global')
      leadName   — display name in the live feed (defaults to 'Demo User')
    """
    # Accept FIRST (Issue 2)
    await websocket.accept()
    print("Connected")

    agent_id    = websocket.query_params.get("agentId",  "default")
    client_id   = websocket.query_params.get("clientId", "global")
    lead_name   = websocket.query_params.get("leadName", "Demo User")
    schema_path = _resolve_schema(agent_id)
    campaign_id = f"demo_mic_{uuid.uuid4().hex[:8]}"
    lead_uid    = f"{campaign_id}_demo"
    transcripts: list[dict] = []

    logger.info("Voice Demo: Connected — agent=%s client=%s campaign=%s", agent_id, client_id, campaign_id)

    try:
        # Create campaign record in DB
        # Note: client_id and agent_id are FK columns — pass None (NULL) to avoid
        # FK constraint errors for demo sessions which aren't tied to real DB rows.
        await db.upsert_campaign(campaign_id, {
            "name":               f"Demo — {lead_name}",
            "status":             "Active",
            "agent_id":           None,           # NULL is allowed in FK cols
            "client_id":          None,           # NULL is allowed in FK cols
            "telephony_provider": "demo_mic",
            "created_at":         datetime.now().isoformat(),
        })
        logger.info("Voice Demo: DB record created — %s", campaign_id)

        # Emit "Ringing" event so the live feed shows a call card immediately
        await ws_manager.send_call_event(
            "call_ringing",
            campaign_id=campaign_id,
            lead_id=lead_uid,
            lead_name=lead_name,
            status="Ringing...",
            snippet="Connecting to agent...",
            provider="demo_mic",
            client_id=client_id,
        )
        try:
            await websocket.send_text(json.dumps({
                "type": "call_ringing",
                "campaign_id": campaign_id,
                "leadId": lead_uid,
                "status": "Ringing...",
                "snippet": "Connecting to agent..."
            }))
        except Exception:
            pass
        logger.info("Voice Demo: Ringing event sent")
    except Exception as _setup_err:
        logger.exception("Voice Demo: Setup FAILED — %s", _setup_err)
        try:
            await websocket.close(code=1011, reason="Setup error")
        except Exception:
            pass
        return

    async def on_transcript(speaker: str, text: str):
        """Called by VoiceLiveSink on every transcript line — forwards to dashboard."""
        role = "assistant" if speaker == "agent" else "user"
        transcripts.append({"role": role, "content": text})

        await ws_manager.send_call_event(
            "call_talking",
            campaign_id=campaign_id,
            lead_id=lead_uid,
            lead_name=lead_name,
            status="Talking",
            snippet=text,
            transcripts=list(transcripts),
            provider="demo_mic",
            client_id=client_id,
        )
        try:
            await websocket.send_text(json.dumps({
                "type": "call_talking",
                "campaign_id": campaign_id,
                "leadId": lead_uid,
                "status": "Talking",
                "snippet": text
            }))
        except Exception:
            pass

    # Keep a reference to the LLM processor so we can read extracted conversation
    # data (budget, location, etc.) from the StateManager after the call ends.
    llm_ref   = None
    source    = None
    runner_task = None
    pipeline_ok = False

    recorder = TimelineSessionRecorder(sample_rate=24000)
    if _PIPECAT_AVAILABLE:
        try:
            source = VoiceLiveSource(recorder=recorder)
            turn_state = VoiceTurnState()
            stt    = RealEstateSTTProcessor(turn_state=turn_state, agent_id=agent_id)
            llm    = RealEstateLLMProcessor()
            llm.state_manager = StateManager(schema_path)
            llm.state_manager.conversation_data["name"] = lead_name
            llm.state_manager.conversation_data["lead_name"] = lead_name
            llm_ref = llm  # capture ref BEFORE runner_task starts
            tts    = RealEstateTTSProcessor(turn_state=turn_state, agent_id=agent_id)
            sink   = VoiceLiveSink(websocket, on_transcript=on_transcript, recorder=recorder)
            logger.info("Voice Demo: Pipeline components created")

            pipeline    = Pipeline([source, stt, llm, tts, sink])
            runner      = PipelineRunner()
            task        = PipelineTask(pipeline)
            runner_task = asyncio.create_task(runner.run(task))
            logger.info("Voice Demo: Pipeline running")
            pipeline_ok = True
        except Exception as _pipe_err:
            logger.exception("Voice Demo: Pipeline creation FAILED — %s", _pipe_err)
            # Do NOT close — fall through to keep-alive fallback loop below
            pipeline_ok = False
    else:
        logger.warning("Voice Demo: pipecat not available — running in keep-alive mode (no AI pipeline)")

    # Emit "Connected" once pipeline is wired (or fallback mode)
    await ws_manager.send_call_event(
        "call_connected",
        campaign_id=campaign_id,
        lead_id=lead_uid,
        lead_name=lead_name,
        status="Connected",
        snippet="Speaking with agent..." if pipeline_ok else "[No AI pipeline — keep-alive mode]",
        provider="demo_mic",
        client_id=client_id,
    )
    try:
        await websocket.send_text(json.dumps({
            "type":        "call_connected",
            "campaign_id": campaign_id,
            "leadId":      lead_uid,
            "status":      "Connected",
            "pipeline":    "active" if pipeline_ok else "unavailable",
        }))
    except Exception:
        pass
    logger.info("Voice Demo: Connected event sent — pipeline_ok=%s", pipeline_ok)
    print("Loop running")

    # ── HEARTBEAT TASK ─────────────────────────────────────────────────────────
    # Railway's reverse proxy drops idle WebSocket connections after ~30 s.
    # Send a JSON ping every 15 s to keep the connection alive regardless of
    # whether the AI pipeline is active.
    _hb_stop = asyncio.Event()

    async def _heartbeat():
        """Server-side keepalive — fires every 15 s."""
        while not _hb_stop.is_set():
            try:
                await asyncio.wait_for(_hb_stop.wait(), timeout=15)
            except asyncio.TimeoutError:
                pass
            if _hb_stop.is_set():
                break
            try:
                await websocket.send_text(json.dumps({"type": "ping"}))
                print("Heartbeat sent")
            except Exception:
                break  # WS already closed

    heartbeat_task = asyncio.create_task(_heartbeat())

    async def reader():
        try:
            while True:
                print("Loop running")
                msg = await websocket.receive()
                if msg["type"] == "websocket.receive":
                    print("Message received")
                    text = msg.get("text")
                    if text:
                        # Handle ping/pong from frontend
                        if text == "ping" or text == "PING":
                            try:
                                await websocket.send_text("pong")
                            except Exception:
                                pass
                            continue
                        try:
                            payload = json.loads(text)
                            if payload.get("type") == "mic_ready" and source is not None:
                                source.set_sample_rate(payload.get("sampleRate", 16000))
                        except Exception:
                            pass
                        continue

                    data = msg.get("bytes") or b""
                    if data:
                        if data == b"ping":
                            try:
                                await websocket.send_bytes(b"pong")
                            except Exception:
                                pass
                            continue
                        if source is not None:
                            source.queue_audio(data)
                elif msg["type"] == "websocket.disconnect":
                    break
        except WebSocketDisconnect:
            print("Client disconnected normally")
        except Exception as e:
            print("WebSocket error:", e)
            logger.error("Voice Demo Reader Task Error: %s", e)

    try:
        await reader()
    finally:
        _hb_stop.set()
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except (asyncio.CancelledError, Exception):
            pass
        print("Closing connection")
        # Tear down pipeline
        try:
            if source._process_task:
                source._process_task.cancel()
            await source.process_frame(EndFrame(), FrameDirection.DOWNSTREAM)
            await asyncio.sleep(0.3)
            runner_task.cancel()
            await runner_task
        except (asyncio.CancelledError, Exception):
            pass

        # ── Extract real lead data from the StateManager conversation_data ──
        duration_s = 0.0
        recording_url = ""
        try:
            filename = f"rec_{lead_uid}.wav"
            filepath = os.path.join("recordings", filename)
            duration_s = recorder.finalize(filepath)
            if duration_s > 0:
                recording_url = f"/recordings/{filename}"
        except Exception as _rec_err:
            logger.warning("Voice Demo: Audio recording failed - %s", _rec_err)

        conv_data: dict = {}
        try:
            if llm_ref and hasattr(llm_ref, "state_manager"):
                conv_data = llm_ref.state_manager.conversation_data or {}
        except Exception as _cd_err:
            logger.warning("Voice Demo: Could not read conversation_data — %s", _cd_err)

        interested = "Yes" if (conv_data.get("intent_value") or conv_data.get("location")) else "No"

        callback_value = conv_data.get("timeline", "—")
        result = {
            "name":          lead_name,
            "phone":         "browser-mic",
            "calledAt":      datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "duration":      f"{len(transcripts) * 8}s (est.)",
            "status":        "Connected",
            "interested":    interested,
            "budget":        conv_data.get("budget", "—"),
            "location":      conv_data.get("location", "—"),
            "timeline":      callback_value,
            "callback":      callback_value,
            "property_type": conv_data.get("property_type", "—"),
            "transcription": transcripts,
            "provider":      "demo_mic",
            "processed":     True,
            "lead_data":     conv_data,  # send raw extracted slots for frontend card
            "recording_url": recording_url,
            "duration":      int(duration_s) if duration_s else len(transcripts) * 8
        }
        logger.info("Voice Demo: Extracted lead data — %s", conv_data)
        await ws_manager.send_call_event(
            "call_completed",
            campaign_id=campaign_id,
            lead_id=lead_uid,
            lead_name=lead_name,
            status="Completed",
            snippet="Demo session ended",
            transcripts=transcripts,
            result=result,
            provider="demo_mic",
            client_id=client_id,
        )
        # Also push the completed result directly to the voice WebSocket so the
        # frontend Demo page (which listens on liveSocket.onmessage) can render
        # the lead summary card without waiting for the dashboard WS.
        try:
            await websocket.send_text(json.dumps({
                "type":   "call_completed",
                "result": result,
                "leadId": lead_uid,
                "leadName": lead_name,
            }))
        except Exception:
            pass  # WebSocket may already be closed — that's fine
        # Persist to DB
        try:
            await db.append_call_result(campaign_id, result)
            await db.update_live_state(lead_uid, campaign_id, lead_name, "Completed", "Demo session ended", transcripts, "demo_mic")
            await db.set_campaign_status(campaign_id, "Done")
        except Exception as e:
            logger.error("Voice Demo DB persist error: %s", e)


# ── Helper ────────────────────────────────────────────────────────────────────
def _resolve_schema(agent_id: str) -> str:
    """
    Resolve the agent schema path from agent_id.
    Always reads from disk — never cached — so fine-tuning changes apply immediately.
    """
    path = os.path.join(AGENTS_DIR, f"{agent_id}.json")
    if os.path.exists(path):
        return path
    default = os.path.join(os.path.dirname(__file__), "Updated_Real_Estate_Agent.json")
    return default


# ── Entry Point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    PORT = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=False)

