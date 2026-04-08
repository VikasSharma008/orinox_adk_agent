"""ORINOX v3 Communication Tools — Gemini generates advisories, DB queues messages."""
import json
from config import generate_content
from tools.registry import get_registry
from db.database import get_db


async def comms_generate_advisory(client_name: str, event_summary: str,
                                   exposure_details: str = "",
                                   client_profile: dict = None) -> dict:
    profile_ctx = json.dumps(client_profile, default=str)[:400] if client_profile else ""
    prompt = f"""Draft a professional advisory email for a wealth management client.
Client: {client_name}
{f'Profile: {profile_ctx}' if profile_ctx else ''}
Market Event: {event_summary}
Exposure: {exposure_details}
Write a professional email (150-200 words): subject line, greeting by first name,
reference specific holdings, clear recommendation, reassuring tone, call-to-action.
JSON: {{"subject":"...","body":"...","recommended_action":"hold|rebalance|schedule_call","urgency":"low|medium|high"}}"""
    try:
        t = generate_content(prompt).strip()
        if "```json" in t: t = t.split("```json")[1].split("```")[0].strip()
        elif "```" in t: t = t.split("```")[1].split("```")[0].strip()
        return json.loads(t)
    except:
        first = client_name.split()[0] if client_name else "Client"
        return {"subject": f"Market Update: {event_summary[:40]}",
                "body": f"Dear {first},\n\nRecent market developments may affect your portfolio. Please contact your relationship manager.\n\nBest regards,\nVikram",
                "recommended_action": "schedule_call", "urgency": "medium"}


async def comms_generate_batch(clients: list, event_summary: str) -> dict:
    prompt = f"""Create an email template for wealth advisory. Event: {event_summary}. Clients: {len(clients)}.
Use placeholders: {{client_name}}, {{holding_names}}, {{exposure_amount}}.
Professional, 150-200 words, include subject.
JSON: {{"subject":"...","body":"...","recommended_action":"hold|rebalance|schedule_call","urgency":"low|medium|high"}}"""
    try:
        t = generate_content(prompt).strip()
        if "```json" in t: t = t.split("```json")[1].split("```")[0].strip()
        elif "```" in t: t = t.split("```")[1].split("```")[0].strip()
        return json.loads(t)
    except:
        return {"subject": "Important Market Advisory",
                "body": "Dear {client_name},\n\nA recent market event may affect your portfolio ({holding_names}). Please contact your RM.\n\nBest regards,\nVikram",
                "recommended_action": "schedule_call", "urgency": "medium"}


async def comms_queue_and_log(client: dict, subject: str, body: str,
                               event_id: str = None, workflow_id: str = None) -> dict:
    db = await get_db()
    personalized = body.replace("{client_name}", client.get("name", "Client"))
    personalized = personalized.replace("{holding_names}", client.get("instrument_name", "your holdings"))
    personalized = personalized.replace("{exposure_amount}", str(client.get("current_value", "N/A")))
    p_subject = subject.replace("{client_name}", client.get("name", "Client"))

    msg = await db.queue_message({"client_id": client["id"], "event_id": event_id,
        "workflow_id": workflow_id, "channel": "email", "subject": p_subject, "content": personalized})

    await db.log_interaction({"client_id": client["id"], "interaction_type": "advisory_queued",
        "channel": "email", "subject": p_subject, "summary": personalized[:200], "logged_by": "comms_agent"})

    return {"client_id": client["id"], "client_name": client.get("name"),
            "email": client.get("email"), "status": "queued", "message_id": msg.get("id")}


def register_comms_tools():
    r = get_registry()
    r.register("comms_generate_advisory", "Generate personalized advisory email using Gemini",
        {"type":"object","properties":{"client_name":{"type":"string"},"event_summary":{"type":"string"},
         "exposure_details":{"type":"string"},"client_profile":{"type":"object"}},
         "required":["client_name","event_summary"]}, comms_generate_advisory, "comms")
    r.register("comms_generate_batch", "Generate batch email template for client segment",
        {"type":"object","properties":{"clients":{"type":"array"},"event_summary":{"type":"string"}},
         "required":["clients","event_summary"]}, comms_generate_batch, "comms")
    r.register("comms_queue_and_log", "Queue personalized message to DB and log interaction",
        {"type":"object","properties":{"client":{"type":"object"},"subject":{"type":"string"},
         "body":{"type":"string"},"event_id":{"type":"string"},"workflow_id":{"type":"string"}},
         "required":["client","subject","body"]}, comms_queue_and_log, "comms")
