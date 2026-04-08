# ORINOX v3 — AI Wealth Advisory Co-Pilot

> Multi-agent orchestration · MCP integration · AlloyDB · Pure Google Stack
> Gen AI Academy APAC Hackathon 2025

## What It Does

One message triggers a chain of AI agents:

*"RBI hiked rates by 50bps. Who's exposed and what should I tell them?"*

1. **Market Agent** — analyzes event via yfinance + Gemini + Fetch MCP (live news)
2. **Client Brief Agent** — segments clients from AlloyDB + stores context in Memory MCP
3. **Comms Agent** — generates advisories via Gemini + saves report via Filesystem MCP
4. **Schedule Agent** — creates follow-up events + exports via Filesystem MCP

All logged with full audit trail. 25+ tools. 3 MCP servers. Zero external licenses.

## Architecture

```
ORCHESTRATOR (ADK + Gemini)
├── Market Agent      → yfinance + Gemini + Fetch MCP (live news)
├── Client Brief      → AlloyDB (direct) + Memory MCP (context graph)
├── Comms Agent       → Gemini (generation) + DB (queue) + Filesystem MCP (reports)
└── Schedule Agent    → DB (events) + Filesystem MCP (exports)
         ↓
     AlloyDB / SQLite (structured + vector)
         ↓
     3 MCP Servers: Fetch · Memory · Filesystem (zero-config, free)
```

## Quick Start

```bash
pip install -r requirements.txt
cp .env.example .env          # add GOOGLE_API_KEY
python -m db.seed_data         # 12 demo clients with portfolios
python app.py                  # http://localhost:8080
```

```bash
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "RBI hiked rates by 50bps. Who is exposed?"}'
```

**Note:** MCP servers require Node.js (npx). Install from nodejs.org. If Node.js is unavailable, all MCP tools gracefully fall back to local implementations.

## Deploy to Cloud Run

```bash
gcloud run deploy orinox --source . --region us-central1 \
  --allow-unauthenticated --set-env-vars="GOOGLE_API_KEY=your-key"
```

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | /chat | Natural language → multi-agent workflow |
| POST | /workflow | Direct workflow execution |
| GET | /clients | List clients |
| GET | /clients/{id}/brief | 360-degree pre-call brief |
| GET | /clients/{id}/portfolio | Holdings |
| GET | /events | Market events |
| GET | /communications | Message queue |
| GET | /schedule | Scheduled events |
| GET | /workflows/{id} | Audit trail |
| GET | /tools | All 25+ registered tools |
| GET | /health | Agents + MCP status |
| GET | /mcp/status | MCP server health |

## Hackathon Requirements Map

| Requirement | Implementation |
|---|---|
| Primary agent + sub-agents | Orchestrator (ADK+Gemini) → 4 sub-agents |
| Structured DB storage | AlloyDB/SQLite — 9 tables, vector search |
| Multiple tools via MCP | Fetch MCP + Memory MCP + Filesystem MCP |
| Multi-step workflows | 4 workflow types, full audit trail |
| API-based deployment | FastAPI on Cloud Run |

## Tech Stack (Zero Cost)

| Component | Technology |
|-----------|-----------|
| Orchestrator | Google ADK + Gemini 1.5 |
| Market Data | yfinance + Gemini search |
| Client Data | AlloyDB (PostgreSQL) |
| MCP: Fetch | @modelcontextprotocol/server-fetch |
| MCP: Memory | @modelcontextprotocol/server-memory |
| MCP: Filesystem | @modelcontextprotocol/server-filesystem |
| Vector Search | Gemini embeddings + pgvector |
| API | FastAPI on Cloud Run |

## Project Structure

```
orinox/
├── app.py, Dockerfile, requirements.txt
├── api/main.py, schemas.py
├── agents/orchestrator.py, market_agent.py, client_brief_agent.py,
│         comms_agent.py, schedule_agent.py, prompts.py
├── tools/registry.py, market_tools.py, client_tools.py,
│        comms_tools.py, schedule_tools.py,
│        mcp_servers.py, fetch_mcp_tools.py,
│        memory_mcp_tools.py, filesystem_mcp_tools.py
├── db/database.py, schema.sql, vector_search.py, seed_data.py
├── tests/
└── docs/
```
