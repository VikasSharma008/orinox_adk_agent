"""ORINOX v3 FastAPI Application"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from api.schemas import ChatRequest, ChatResponse, WorkflowRequest, HealthResponse
from agents.orchestrator import Orchestrator
from db.database import get_db
from tools.registry import get_registry
from tools.market_tools import register_market_tools
from tools.client_tools import register_client_tools
from tools.comms_tools import register_comms_tools
from tools.schedule_tools import register_schedule_tools
from tools.fetch_mcp_tools import register_fetch_mcp_tools
from tools.memory_mcp_tools import register_memory_mcp_tools
from tools.filesystem_mcp_tools import register_filesystem_mcp_tools
from tools.mcp_servers import start_mcp_servers, stop_mcp_servers, get_mcp_status


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = await get_db()
    # Register all direct tools
    register_market_tools()
    register_client_tools()
    register_comms_tools()
    register_schedule_tools()
    # Register MCP tools
    register_fetch_mcp_tools()
    register_memory_mcp_tools()
    register_filesystem_mcp_tools()
    # Start MCP servers
    print("Starting MCP servers...")
    start_mcp_servers()
    reg = get_registry()
    print(f"ORINOX v3 ready — {len(reg.names)} tools registered")
    yield
    stop_mcp_servers()

app = FastAPI(title="ORINOX", description="AI Wealth Advisory Co-Pilot v3", version="3.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
orchestrator = Orchestrator()


@app.get("/health", response_model=HealthResponse)
async def health():
    reg = get_registry()
    mcp = get_mcp_status()
    return HealthResponse(
        agents=["ORCHESTRATOR", "MARKET_AGENT", "CLIENT_BRIEF_AGENT", "COMMS_AGENT", "SCHEDULE_AGENT"],
        tools_count=len(reg.names),
        mcp_servers=mcp)


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    try:
        r = await orchestrator.process(req.message)
        return ChatResponse(**r)
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/workflow")
async def workflow(req: WorkflowRequest):
    try:
        msg_map = {
            "market_event_response": req.params.get("event_description", "Market event"),
            "pre_call_brief": f"Brief me on {req.params.get('client_name', 'the client')}",
            "schedule_followups": f"Schedule follow-ups for {req.params.get('risk_profile', 'high-risk')} clients",
            "research_query": req.params.get("query", "Research request"),
        }
        return await orchestrator.process(msg_map.get(req.intent, str(req.params)))
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/clients")
async def list_clients(segment: str = None, risk: str = None, limit: int = Query(100, ge=1, le=500)):
    db = await get_db()
    return {"total": len(c := await db.list_clients(segment=segment, risk=risk, limit=limit)), "clients": c}


@app.get("/clients/{client_id}")
async def get_client(client_id: str):
    db = await get_db()
    c = await db.get_client(client_id)
    if not c: raise HTTPException(404, "Client not found")
    return c


@app.get("/clients/{client_id}/brief")
async def get_brief(client_id: str):
    return await orchestrator.client_brief.generate_pre_call_brief(client_id=client_id)


@app.get("/clients/{client_id}/portfolio")
async def get_portfolio(client_id: str):
    db = await get_db()
    h = await db.get_portfolio(client_id)
    return {"client_id": client_id, "total_value": sum(x.get("current_value", 0) for x in h), "holdings": h}


@app.get("/clients/{client_id}/household")
async def get_household(client_id: str):
    db = await get_db()
    return {"client_id": client_id, "members": await db.get_household(client_id)}


@app.get("/events")
async def list_events(limit: int = Query(20, ge=1, le=100)):
    db = await get_db()
    return {"events": await db.list_market_events(limit)}


@app.get("/communications")
async def list_comms(workflow_id: str = None, status: str = None, limit: int = Query(50)):
    db = await get_db()
    return {"messages": await db.list_communications(workflow_id, status, limit)}


@app.get("/schedule")
async def list_schedule(workflow_id: str = None, limit: int = Query(50)):
    db = await get_db()
    return {"events": await db.list_scheduled_events(workflow_id, limit)}


@app.get("/workflows/{workflow_id}")
async def get_workflow(workflow_id: str):
    db = await get_db()
    logs = await db.get_workflow_log(workflow_id)
    if not logs: raise HTTPException(404, "Workflow not found")
    return {"workflow_id": workflow_id, "steps": logs}


@app.get("/tools")
async def list_tools():
    reg = get_registry()
    return {"total": len(reg.names), "tools": reg.all_schemas()}


@app.get("/mcp/status")
async def mcp_status():
    return {"mcp_servers": get_mcp_status()}
