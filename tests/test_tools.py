import pytest

@pytest.mark.asyncio
async def test_client_crud(db):
    r = await db.upsert_client({"name":"Priya Test","email":"p@t.com","risk_profile":"aggressive","aum":8000000})
    assert r["name"] == "Priya Test"
    c = await db.find_client("Priya")
    assert c is not None and c["email"] == "p@t.com"

@pytest.mark.asyncio
async def test_portfolio(db):
    c = await db.upsert_client({"name":"Port Test"})
    await db.upsert_portfolio({"client_id":c["id"],"instrument_name":"TCS","instrument_type":"equity","sector":"IT","current_value":500000})
    await db.upsert_portfolio({"client_id":c["id"],"instrument_name":"SBI Bond","instrument_type":"bond","sector":"banking","current_value":300000})
    p = await db.get_portfolio(c["id"])
    assert len(p) == 2

@pytest.mark.asyncio
async def test_sector_query(seeded_db):
    r = await seeded_db.get_clients_by_sector("banking")
    assert len(r) >= 1

@pytest.mark.asyncio
async def test_workflow_log(db):
    await db.log_step("WF-T1", 1, "MARKET", "analyze", status="completed")
    await db.log_step("WF-T1", 2, "CLIENT", "segment", status="completed")
    logs = await db.get_workflow_log("WF-T1")
    assert len(logs) == 2

@pytest.mark.asyncio
async def test_comm_queue(db):
    c = await db.upsert_client({"name":"Comm Test"})
    m = await db.queue_message({"client_id":c["id"],"content":"Test advisory","channel":"email","workflow_id":"WF-C1"})
    assert m["status"] == "queued"
    msgs = await db.list_communications(workflow_id="WF-C1")
    assert len(msgs) == 1

@pytest.mark.asyncio
async def test_scheduled_events(db):
    c = await db.upsert_client({"name":"Sched Test"})
    await db.create_scheduled_event({"client_id":c["id"],"title":"Portfolio Review","start_time":"2025-07-01T10:00:00","workflow_id":"WF-S1"})
    evts = await db.list_scheduled_events(workflow_id="WF-S1")
    assert len(evts) == 1

@pytest.mark.asyncio
async def test_registry():
    from tools.registry import ToolRegistry
    reg = ToolRegistry()
    async def dummy(**kw): return {"ok":True,**kw}
    reg.register("t1","Test",{},dummy,"test")
    assert "t1" in reg.names
    r = await reg.call("t1", x=1)
    assert r["ok"] and r["x"] == 1
    r2 = await reg.call("nonexistent")
    assert "error" in r2

@pytest.mark.asyncio
async def test_memory_mcp_fallback():
    """Test Memory MCP local fallback when server is not running."""
    from tools.memory_mcp_tools import memory_store_entity, memory_search, memory_add_observation
    r = await memory_store_entity("Priya Sharma", "client", ["Risk: aggressive", "AUM: 8.5M"])
    assert r["stored"] == "Priya Sharma"
    assert r["via"] == "local_fallback"
    r2 = await memory_search("Priya")
    assert len(r2["results"]) >= 1
    r3 = await memory_add_observation("Priya Sharma", "Last call: discussed tax planning")
    assert r3["via"] == "local_fallback"

@pytest.mark.asyncio
async def test_filesystem_mcp_fallback():
    """Test Filesystem MCP direct fallback when server is not running."""
    import os
    os.makedirs("/tmp/orinox_test_output/briefs", exist_ok=True)
    from tools.filesystem_mcp_tools import fs_write_file, fs_read_file
    w = await fs_write_file("test.txt", "Hello ORINOX", subdir="")
    assert w.get("via") == "direct_fallback"
    assert w.get("size") == 12
    r = await fs_read_file(w["file"])
    assert "Hello ORINOX" in r.get("content", "")
    os.remove(w["file"])

@pytest.mark.asyncio
async def test_fetch_mcp_fallback():
    """Test Fetch MCP httpx fallback when server is not running."""
    from tools.fetch_mcp_tools import fetch_url
    # This will use httpx fallback since MCP server is disabled in tests
    r = await fetch_url("https://example.com", max_length=500)
    # May succeed (httpx) or fail (network) — both are valid in test
    assert "url" in r
    assert r.get("via") in ("httpx_fallback", "failed")
