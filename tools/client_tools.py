"""ORINOX v2 Client Tools — AlloyDB direct queries for client data"""
from tools.registry import get_registry
from db.database import get_db

async def client_get_profile(client_name: str = None, client_id: str = None) -> dict:
    db = await get_db()
    if client_id: return await db.get_client(client_id) or {"error": "Not found"}
    if client_name: return await db.find_client(client_name) or {"error": "Not found"}
    return {"error": "Provide client_name or client_id"}

async def client_get_portfolio(client_id: str) -> dict:
    db = await get_db()
    holdings = await db.get_portfolio(client_id)
    total = sum(h.get("current_value",0) for h in holdings)
    return {"client_id":client_id,"total_value":total,"count":len(holdings),"holdings":holdings}

async def client_get_household(client_id: str) -> dict:
    db = await get_db()
    members = await db.get_household(client_id)
    return {"client_id":client_id,"count":len(members),"members":members}

async def client_get_interactions(client_id: str, limit: int = 10) -> dict:
    db = await get_db()
    ixns = await db.get_client_interactions(client_id, limit)
    return {"client_id":client_id,"count":len(ixns),"interactions":ixns}

async def client_segment_by_criteria(sector: str = None, instrument_type: str = None,
                                      risk_profile: str = None, min_aum: float = None) -> dict:
    db = await get_db()
    results = []
    if sector: results = await db.get_clients_by_sector(sector)
    elif instrument_type: results = await db.get_clients_by_instrument_type(instrument_type)
    else: results = await db.list_clients(limit=500)
    if risk_profile: results = [c for c in results if c.get("risk_profile") == risk_profile]
    if min_aum: results = [c for c in results if c.get("aum",0) >= min_aum]
    seen, unique = set(), []
    for r in results:
        if r["id"] not in seen: seen.add(r["id"]); unique.append(r)
    return {"total":len(unique),"filter":{"sector":sector,"instrument_type":instrument_type,"risk_profile":risk_profile,"min_aum":min_aum},"clients":unique}

async def client_get_360(client_id: str = None, client_name: str = None) -> dict:
    profile = await client_get_profile(client_name=client_name, client_id=client_id)
    if "error" in profile: return profile
    cid = profile["id"]
    return {"profile":profile, "portfolio":await client_get_portfolio(cid),
            "household":await client_get_household(cid),
            "recent_interactions":await client_get_interactions(cid, 5)}

def register_client_tools():
    r = get_registry()
    r.register("client_get_profile","Get client demographics and preferences from AlloyDB",
        {"type":"object","properties":{"client_name":{"type":"string"},"client_id":{"type":"string"}}},
        client_get_profile, "client")
    r.register("client_get_portfolio","Get client financial holdings and allocations",
        {"type":"object","properties":{"client_id":{"type":"string"}},"required":["client_id"]},
        client_get_portfolio, "client")
    r.register("client_get_household","Get family members and dependents",
        {"type":"object","properties":{"client_id":{"type":"string"}},"required":["client_id"]},
        client_get_household, "client")
    r.register("client_get_interactions","Get recent activity history",
        {"type":"object","properties":{"client_id":{"type":"string"},"limit":{"type":"integer"}},"required":["client_id"]},
        client_get_interactions, "client")
    r.register("client_segment_by_criteria","Segment clients by sector, instrument type, risk profile, or AUM",
        {"type":"object","properties":{"sector":{"type":"string"},"instrument_type":{"type":"string"},"risk_profile":{"type":"string"},"min_aum":{"type":"number"}}},
        client_segment_by_criteria, "client")
    r.register("client_get_360","Full 360-degree client view for pre-call briefs",
        {"type":"object","properties":{"client_id":{"type":"string"},"client_name":{"type":"string"}}},
        client_get_360, "client")
