import pytest, os
os.environ["USE_SQLITE"] = "true"
os.environ["SQLITE_PATH"] = "orinox_test.db"
os.environ["MCP_FETCH_ENABLED"] = "false"
os.environ["MCP_MEMORY_ENABLED"] = "false"
os.environ["MCP_FILESYSTEM_ENABLED"] = "false"

@pytest.mark.asyncio
async def test_fallback_market():
    from agents.orchestrator import Orchestrator
    o = Orchestrator()
    p = o._fallback_plan("RBI hiked rates by 50bps. Who is exposed?")
    assert p["intent"] == "market_event_response"
    assert len(p["plan"]) == 4
    assert p["plan"][0]["agent"] == "MARKET_AGENT"
    assert p["plan"][3]["agent"] == "SCHEDULE_AGENT"

@pytest.mark.asyncio
async def test_fallback_brief():
    from agents.orchestrator import Orchestrator
    o = Orchestrator()
    p = o._fallback_plan("Brief me on Priya Sharma before my call")
    assert p["intent"] == "pre_call_brief"

@pytest.mark.asyncio
async def test_fallback_schedule():
    from agents.orchestrator import Orchestrator
    o = Orchestrator()
    p = o._fallback_plan("Schedule portfolio review calls with high-risk clients next week")
    assert p["intent"] == "schedule_followups"

@pytest.mark.asyncio
async def test_fallback_research():
    from agents.orchestrator import Orchestrator
    o = Orchestrator()
    p = o._fallback_plan("Email the research desk about IT sector outlook")
    assert p["intent"] == "research_query"

@pytest.mark.asyncio
async def test_all_tools_registered():
    """Verify all tools are registered on startup."""
    from tools.registry import get_registry
    from tools.market_tools import register_market_tools
    from tools.client_tools import register_client_tools
    from tools.comms_tools import register_comms_tools
    from tools.schedule_tools import register_schedule_tools
    from tools.fetch_mcp_tools import register_fetch_mcp_tools
    from tools.memory_mcp_tools import register_memory_mcp_tools
    from tools.filesystem_mcp_tools import register_filesystem_mcp_tools

    # Use a fresh registry
    from tools.registry import ToolRegistry
    reg = ToolRegistry()
    import tools.registry as mod
    old = mod._reg
    mod._reg = reg

    register_market_tools()
    register_client_tools()
    register_comms_tools()
    register_schedule_tools()
    register_fetch_mcp_tools()
    register_memory_mcp_tools()
    register_filesystem_mcp_tools()

    names = reg.names
    print(f"Registered {len(names)} tools: {names}")

    # Direct tools
    assert "market_search" in names
    assert "market_analyze_impact" in names
    assert "client_get_360" in names
    assert "client_segment_by_criteria" in names
    assert "comms_generate_advisory" in names
    assert "comms_queue_and_log" in names
    assert "schedule_batch_followups" in names

    # MCP tools
    assert "fetch_url" in names
    assert "fetch_market_news" in names
    assert "memory_store_entity" in names
    assert "memory_search" in names
    assert "memory_store_client_context" in names
    assert "fs_write_file" in names
    assert "fs_save_brief" in names
    assert "fs_save_advisory_report" in names
    assert "fs_save_schedule_export" in names

    assert len(names) >= 25

    mod._reg = old

@pytest.mark.asyncio
async def test_health_endpoint():
    from fastapi.testclient import TestClient
    from api.main import app
    with TestClient(app) as client:
        r = client.get("/health")
        assert r.status_code == 200
        d = r.json()
        assert d["status"] == "healthy"
        assert d["version"] == "3.0.0"
        assert "SCHEDULE_AGENT" in d["agents"]
        assert d["tools_count"] >= 25
        assert "fetch" in d["mcp_servers"]
        assert "memory" in d["mcp_servers"]
        assert "filesystem" in d["mcp_servers"]
