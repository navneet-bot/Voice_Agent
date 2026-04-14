import asyncio
import json
import os
import random
from datetime import datetime
from llm.state_manager import StateManager
from llm.llm import generate_response, extract_intent

# Base directories
DB_DIR = "db"
AGENTS_DIR = os.path.join(DB_DIR, "agents")
CAMPAIGNS_FILE = os.path.join(DB_DIR, "campaigns.json")
LEADS_FILE = os.path.join(DB_DIR, "leads.json")

def read_json(path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except:
        return []

def write_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=4)

async def simulate_human_response(agent_text, lead_name):
    """
    Simulates a human reply based on the agent's question.
    In a real scenario, this would be the STT output.
    """
    t = agent_text.lower()
    if "speaking with" in t or "hello" in t:
        return f"Yes, this is {lead_name}."
    if "good time" in t or "quick two-minute" in t:
        return "Yeah, I have a moment."
    if "buy, rent, or invest" in t:
        return "I'm looking to buy a property."
    if "location" in t or "budget" in t:
        locations = ["Wakad", "Baner", "Hinjewadi", "Kharadi"]
        return f"I'm interested in {random.choice(locations)} within 80 lakhs budget."
    if "site visit" in t:
        return "Yes, I can visit this Sunday."
    if "date and time" in t:
        return "Sunday morning 11 AM works for me."
    
    return "Okay, that sounds good."

async def run_campaign(campaign_id: str, agent_id: str):
    """Executes a campaign by running the agent logic for every lead."""
    leads_db = read_json(LEADS_FILE)
    campaign_leads = next((item["leads"] for item in leads_db if item["campaignId"] == campaign_id), [])
    
    if not campaign_leads:
        print(f"No leads found for campaign {campaign_id}")
        return

    # Load agent schema
    agent_path = os.path.join(AGENTS_DIR, f"{agent_id}.json")
    if not os.path.exists(agent_path):
        agent_path = "Updated_Real_Estate_Agent.json"

    # Initialize Live Monitor State
    LIVE_STATE_FILE = os.path.join(DB_DIR, "live_state.json")
    def update_live_state(lead_id, name, status, snippet="", transcripts=[]):
        for _ in range(3): # Retry on lock
            try:
                state = read_json(LIVE_STATE_FILE)
                if not isinstance(state, dict): state = {}
                state[lead_id] = {
                    "campaignId": campaign_id,
                    "name": name,
                    "status": status,
                    "snippet": snippet,
                    "transcripts": transcripts,
                    "lastUpdate": datetime.now().isoformat()
                }
                write_json(LIVE_STATE_FILE, state)
                break
            except Exception:
                time.sleep(0.1)

    for lead in campaign_leads:
        lead_uid = f"{campaign_id}_{lead['phone']}"
        print(f"Starting call for {lead['name']} ({lead['phone']})...")
        update_live_state(lead_uid, lead['name'], "Ringing...")
        
        state_manager = StateManager(agent_path)
        transcripts = []
        
        # 1. Initial Greeting
        response = await generate_response("[System: The call has just been connected.]", [], state_manager=state_manager, allow_transition=False)
        transcripts.append({"role": "assistant", "content": response})
        update_live_state(lead_uid, lead['name'], "Talking", response, transcripts)
        
        turns = 0
        while not state_manager.is_terminal_node() and turns < 10:
            user_text = await simulate_human_response(response, lead['name'])
            transcripts.append({"role": "user", "content": user_text})
            update_live_state(lead_uid, lead['name'], "Talking", user_text, transcripts)
            
            response = await generate_response(user_text, [], state_manager=state_manager)
            transcripts.append({"role": "assistant", "content": response})
            update_live_state(lead_uid, lead['name'], "Talking", response, transcripts)
            turns += 1
            await asyncio.sleep(1.5) # Simulate natural pauses

        # 2. Record results
        campaigns = read_json(CAMPAIGNS_FILE)
        campaign = next((c for c in campaigns if c["id"] == campaign_id), None)
        if campaign:
            result = {
                "name": lead.get("name"),
                "phone": lead.get("phone"),
                "calledAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "duration": f"{turns * 10}s",
                "status": "Connected",
                "interested": "Yes" if state_manager.conversation_data.get("location") else "No",
                "budget": state_manager.conversation_data.get("budget", "—"),
                "callback": state_manager.conversation_data.get("timeline", "—"),
                "transcription": transcripts,
                "processed": True
            }
            campaign["results"].append(result)
            write_json(CAMPAIGNS_FILE, campaigns)
        
        update_live_state(lead_uid, lead['name'], "Completed", "Call ended", transcripts)
        await asyncio.sleep(1) # Gap between calls

    # Mark campaign as done
    campaigns = read_json(CAMPAIGNS_FILE)
    campaign = next((c for c in campaigns if c["id"] == campaign_id), None)
    if campaign:
        campaign["status"] = "Done"
        write_json(CAMPAIGNS_FILE, campaigns)
