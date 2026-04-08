import os, pytest, asyncio
os.environ["USE_SQLITE"] = "true"
os.environ["SQLITE_PATH"] = "orinox_test.db"
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY", "test-key")
os.environ["MCP_FETCH_ENABLED"] = "false"
os.environ["MCP_MEMORY_ENABLED"] = "false"
os.environ["MCP_FILESYSTEM_ENABLED"] = "false"
os.environ["MCP_FS_ROOT"] = "/tmp/orinox_test_output"

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def db():
    from db.database import DatabaseManager
    m = DatabaseManager()
    m._path = "orinox_test.db"
    await m.init()
    yield m
    if os.path.exists("orinox_test.db"): os.remove("orinox_test.db")

@pytest.fixture
async def seeded_db(db):
    c1 = await db.upsert_client({"name":"Test Alpha","email":"a@test.com","risk_profile":"aggressive","aum":10000000})
    c2 = await db.upsert_client({"name":"Test Beta","email":"b@test.com","risk_profile":"conservative","aum":5000000})
    await db.upsert_portfolio({"client_id":c1["id"],"instrument_name":"TCS","instrument_type":"equity","sector":"IT","current_value":4000000,"allocation_pct":40})
    await db.upsert_portfolio({"client_id":c1["id"],"instrument_name":"HDFC Bank","instrument_type":"equity","sector":"banking","current_value":3000000,"allocation_pct":30})
    await db.upsert_portfolio({"client_id":c2["id"],"instrument_name":"Govt Bond 10Y","instrument_type":"government_bond","sector":"sovereign","current_value":4000000,"allocation_pct":80})
    yield db
