"""
ORINOX v3 Schedule Tools — DB-based event scheduling + Filesystem MCP export
"""
import json
from datetime import datetime, timedelta
from tools.registry import get_registry
from db.database import get_db


async def schedule_create_event(title: str, start_time: str, end_time: str = None,
                                 description: str = "", attendees: list = None,
                                 client_id: str = None, workflow_id: str = None) -> dict:
    """Create a scheduled event in AlloyDB."""
    if not end_time:
        try:
            st = datetime.fromisoformat(start_time)
            end_time = (st + timedelta(minutes=30)).isoformat()
        except:
            end_time = start_time
    db = await get_db()
    result = await db.create_scheduled_event({
        "client_id": client_id, "workflow_id": workflow_id, "title": title,
        "description": description, "start_time": start_time, "end_time": end_time,
        "attendees": attendees or []})
    return {"title": title, "start_time": start_time, "end_time": end_time,
            "status": "scheduled", "attendees": attendees or []}


async def schedule_list_events(start_after: str = None, workflow_id: str = None,
                                limit: int = 20) -> dict:
    """List scheduled events from DB."""
    db = await get_db()
    events = await db.list_scheduled_events(workflow_id=workflow_id, limit=limit)
    return {"count": len(events), "events": events}


async def schedule_find_free_slots(date: str, duration_minutes: int = 30,
                                    start_hour: int = 9, end_hour: int = 18) -> dict:
    """Generate available time slots for a given date."""
    slots = []
    hour = start_hour
    while hour + (duration_minutes / 60) <= end_hour:
        s = f"{date}T{hour:02d}:00:00"
        eh = hour + (duration_minutes // 60)
        em = duration_minutes % 60
        e = f"{date}T{eh:02d}:{em:02d}:00"
        slots.append({"start": s, "end": e})
        hour += 1
    return {"date": date, "slots": slots, "count": len(slots)}


async def schedule_batch_followups(clients: list, date_start: str,
                                    title_template: str = "Portfolio Review: {client_name}",
                                    duration_minutes: int = 30,
                                    workflow_id: str = None) -> dict:
    """Schedule follow-up calls for a batch of clients across available slots."""
    try:
        base = datetime.fromisoformat(date_start)
    except:
        base = datetime.now() + timedelta(days=1)

    all_slots = []
    for offset in range(7):
        d = base + timedelta(days=offset)
        if d.weekday() >= 5:
            continue
        free = await schedule_find_free_slots(d.strftime("%Y-%m-%d"), duration_minutes)
        all_slots.extend(free.get("slots", []))
        if len(all_slots) >= len(clients):
            break

    scheduled = []
    for i, client in enumerate(clients):
        if i >= len(all_slots):
            break
        slot = all_slots[i]
        title = title_template.replace("{client_name}", client.get("name", "Client"))
        await schedule_create_event(
            title=title, start_time=slot["start"], end_time=slot["end"],
            description=f"Follow-up with {client.get('name')}. Auto-scheduled by ORINOX.",
            attendees=[client.get("email", "")] if client.get("email") else [],
            client_id=client.get("id"), workflow_id=workflow_id)
        scheduled.append({"client_name": client.get("name"), "client_id": client.get("id"),
                          "start": slot["start"], "end": slot["end"], "status": "scheduled"})

    return {"total_scheduled": len(scheduled), "events": scheduled}


def register_schedule_tools():
    r = get_registry()
    r.register("schedule_create_event", "Create a scheduled event (call, meeting, follow-up) in DB",
        {"type":"object","properties":{"title":{"type":"string"},"start_time":{"type":"string"},
         "end_time":{"type":"string"},"description":{"type":"string"},
         "attendees":{"type":"array","items":{"type":"string"}},
         "client_id":{"type":"string"},"workflow_id":{"type":"string"}},
         "required":["title","start_time"]}, schedule_create_event, "schedule")
    r.register("schedule_list_events", "List scheduled events from DB",
        {"type":"object","properties":{"workflow_id":{"type":"string"},"limit":{"type":"integer"}}},
        schedule_list_events, "schedule")
    r.register("schedule_find_free_slots", "Find available time slots on a date",
        {"type":"object","properties":{"date":{"type":"string"},"duration_minutes":{"type":"integer"}},
         "required":["date"]}, schedule_find_free_slots, "schedule")
    r.register("schedule_batch_followups", "Schedule follow-up calls for a batch of clients",
        {"type":"object","properties":{"clients":{"type":"array"},"date_start":{"type":"string"},
         "title_template":{"type":"string"},"workflow_id":{"type":"string"}},
         "required":["clients","date_start"]}, schedule_batch_followups, "schedule")
