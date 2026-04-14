from fastapi import FastAPI, HTTPException, BackgroundTasks
import asyncio
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import json
import os
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

# Import local modules
from llm.state_manager import StateManager
from agent_runner import run_campaign

import base64
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineTask
from pipecat.frames.frames import AudioRawFrame, EndFrame, TextFrame
from pipecat.processors.frame_processor import FrameProcessor, FrameDirection
from fastapi import WebSocket, WebSocketDisconnect
from flows.runtime import RealEstateSTTProcessor, RealEstateLLMProcessor, RealEstateTTSProcessor

app = FastAPI(title="Cosmic Chameleon Voice Agent Platform")

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Constants
DB_DIR = "db"
AGENTS_DIR = os.path.join(DB_DIR, "agents")
AGENTS_LIST_FILE = os.path.join(DB_DIR, "agents.json")
CAMPAIGNS_FILE = os.path.join(DB_DIR, "campaigns.json")
LEADS_FILE = os.path.join(DB_DIR, "leads.json")
ASSIGNMENTS_FILE = os.path.join(DB_DIR, "assignments.json")
MAX_RETRIES = 3

# Ensure directories exist
os.makedirs(DB_DIR, exist_ok=True)
os.makedirs(AGENTS_DIR, exist_ok=True)

def init_db():
    for file, default in [(AGENTS_LIST_FILE, []), (CAMPAIGNS_FILE, []), (LEADS_FILE, []), (ASSIGNMENTS_FILE, {})]:
        if not os.path.exists(file):
            with open(file, "w") as f:
                json.dump(default, f)

init_db()

# Models
class AgentCreate(BaseModel):
    name: str
    voice: str
    language: str
    max_duration: int
    provider: str
    script: str
    data_fields: List[str]

class LeadsUpload(BaseModel):
    campaignId: str
    leads: List[dict]

class CampaignStart(BaseModel):
    campaignId: str
    agentId: Optional[str] = None

class AssignmentUpdate(BaseModel):
    clientId: str
    agentId: str

# Helper functions
def read_json(path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except:
        return []

def write_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=4)

# Routes
@app.get("/")
async def get_index():
    return FileResponse("voice_agent_platform_v2.html")

@app.get("/api/dashboard")
async def get_dashboard():
    campaigns = read_json(CAMPAIGNS_FILE)
    agents = read_json(AGENTS_LIST_FILE)
    total_calls = sum(len(c.get("results", [])) for c in campaigns)
    return {
        "totalClients": 3,
        "activeAgents": len(agents) or 3,
        "calls": total_calls or 570,
        "connectRate": 38.5
    }

@app.post("/api/agents")
async def create_agent(agent: AgentCreate):
    agents_list = read_json(AGENTS_LIST_FILE)
    agent_id = str(uuid.uuid4())
    
    # 1. Generate full schema using StateManager template
    # Mapping UI voice names to ElevenLabs IDs if possible, else use strings
    voice_map = {"ElevenLabs — Priya (Female)": "11labs-06nek6zjTCD1vCbtc8bc"}
    voice_id = voice_map.get(agent.voice, agent.voice)
    
    agent_schema = StateManager.template_new_agent(
        name=agent.name,
        script=agent.script,
        voice_id=voice_id,
        data_fields=agent.data_fields
    )
    
    # 2. Save full schema to db/agents/
    schema_path = os.path.join(AGENTS_DIR, f"{agent_id}.json")
    write_json(schema_path, agent_schema)
    
    # 3. Add to list for UI
    new_agent_meta = agent.dict()
    new_agent_meta["id"] = agent_id
    new_agent_meta["schema_path"] = schema_path
    new_agent_meta["createdAt"] = datetime.now().isoformat()
    agents_list.append(new_agent_meta)
    
    write_json(AGENTS_LIST_FILE, agents_list)
    return new_agent_meta

@app.get("/api/agents")
async def list_agents():
    return read_json(AGENTS_LIST_FILE)

@app.post("/api/leads/upload")
async def upload_leads(data: LeadsUpload):
    leads_db = read_json(LEADS_FILE)
    existing = next((item for item in leads_db if item["campaignId"] == data.campaignId), None)
    if existing:
        existing["leads"] = data.leads
    else:
        leads_db.append({
            "campaignId": data.campaignId,
            "leads": data.leads,
            "createdAt": datetime.now().isoformat()
        })
    write_json(LEADS_FILE, leads_db)
    
    campaigns = read_json(CAMPAIGNS_FILE)
    c_existing = next((c for c in campaigns if c["id"] == data.campaignId), None)
    if not c_existing:
        campaigns.append({
            "id": data.campaignId,
            "status": "Pending",
            "results": [],
            "createdAt": datetime.now().isoformat()
        })
    else:
        c_existing["status"] = "Pending"
        c_existing["results"] = []
    write_json(CAMPAIGNS_FILE, campaigns)
    return {"status": "success"}

@app.post("/api/campaigns/start")
async def start_campaign(data: CampaignStart, background_tasks: BackgroundTasks):
    campaigns = read_json(CAMPAIGNS_FILE)
    campaign = next((c for c in campaigns if c["id"] == data.campaignId), None)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
        
    campaign["status"] = "Active"
    campaign["results"] = [] # Clear previous if restarting
    write_json(CAMPAIGNS_FILE, campaigns)
    
    # Use assigned agent or default
    agent_id = data.agentId or "default"
    
    background_tasks.add_task(run_campaign, data.campaignId, agent_id)
    return {"status": "started"}

@app.get("/api/campaigns/{campaign_id}/results")
async def get_results(campaign_id: str):
    campaigns = read_json(CAMPAIGNS_FILE)
    for c in campaigns:
        if c["id"] == campaign_id:
            return c["results"]
    return []

@app.get("/api/assignments/{client_id}")
async def get_assignment(client_id: str):
    assignments = read_json(ASSIGNMENTS_FILE)
    agent_id = assignments.get(client_id)
    if not agent_id:
        return {"agentId": None}
    
    agents = read_json(AGENTS_LIST_FILE)
    agent = next((a for a in agents if a["id"] == agent_id), None)
    return {"agentId": agent_id, "agent": agent}

@app.post("/api/assignments")
async def update_assignment(data: AssignmentUpdate):
    assignments = read_json(ASSIGNMENTS_FILE)
    assignments[data.clientId] = data.agentId
    write_json(ASSIGNMENTS_FILE, assignments)
    return {"status": "success"}

# --- Telephony Monitoring & Simulation (Phase 10) ---

LIVE_STATE_FILE = os.path.join(DB_DIR, "live_state.json")

@app.get("/api/campaigns/{campaign_id}/live")
async def get_live_state(campaign_id: str):
    state = read_json(LIVE_STATE_FILE)
    if not isinstance(state, dict): return []
    # Return list of active/last calls for this campaign
    return [v for k, v in state.items() if v.get("campaignId") == campaign_id]

@app.get("/api/telephony/numbers")
async def list_numbers():
    return [
        {"phone": "+91 9122 334455", "region": "Mumbai, IN", "assigned": "Realty Pro Inc."},
        {"phone": "+91 9155 667788", "region": "Bangalore, IN", "assigned": "FinServ Co"}
    ]

@app.post("/api/telephony/buy")
async def buy_number():
    return {"status": "success", "phone": "+91 9122 " + str(uuid.uuid4().int)[:6]} # Mock purchase

# --- Live Voice Support (Phase 8) ---

class VoiceLiveSource(FrameProcessor):
    async def process_frame(self, frame, direction):
        await self.push_frame(frame, direction)

class VoiceLiveSink(FrameProcessor):
    def __init__(self, websocket: WebSocket):
        super().__init__()
        self.ws = websocket

    async def process_frame(self, frame, direction):
        if isinstance(frame, AudioRawFrame):
            # Send raw binary audio to browser for performance
            try:
                await self.ws.send_bytes(frame.audio)
            except:
                pass
        await self.push_frame(frame, direction)

@app.websocket("/api/voice-live")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("Live Voice: Browser connected")

    source = VoiceLiveSource()
    stt = RealEstateSTTProcessor()
    llm = RealEstateLLMProcessor()
    tts = RealEstateTTSProcessor()
    sink = VoiceLiveSink(websocket)

    pipeline = Pipeline([source, stt, llm, tts, sink])
    runner = PipelineRunner()
    task = PipelineTask(pipeline)

    runner_task = asyncio.create_task(runner.run(task))

    try:
        while True:
            # Browser sends 16kHz PCM16 mono audio bytes
            data = await websocket.receive_bytes()
            # Push into STT
            await source.push_frame(
                AudioRawFrame(audio=data, sample_rate=16000, num_channels=1), 
                FrameDirection.DOWNSTREAM
            )
    except WebSocketDisconnect:
        print("Live Voice: Browser disconnected")
    except Exception as e:
        print(f"Live Voice Error: {e}")
    finally:
        await source.push_frame(EndFrame(), FrameDirection.DOWNSTREAM)
        await runner_task

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)
