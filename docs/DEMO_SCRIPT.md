# ORINOX v3 Demo Script (3 minutes)

## Pre-Recording

```bash
curl https://YOUR-URL/health | python -m json.tool    # check agents + MCP status
curl https://YOUR-URL/tools | python -m json.tool     # verify 25+ tools
curl https://YOUR-URL/mcp/status | python -m json.tool # MCP servers running
```

## 0:00-0:15 — Intro

"ORINOX is a multi-agent AI system for wealth management. One message triggers four coordinated agents that analyze markets, segment clients, generate personalized advisories, and schedule follow-ups — all through MCP-integrated tools deployed on Google Cloud."

## 0:15-1:30 — Hero Demo: Market Event Response

```bash
curl -s -X POST https://YOUR-URL/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "RBI just hiked rates by 50bps. Who is exposed and what should I tell them?"}' \
  | python -m json.tool
```

Walk through:
- "Orchestrator created a 6-step plan"
- "Market Agent analyzed impact — used Fetch MCP to pull live RBI news"
- "Client Brief Agent segmented X clients from AlloyDB"
- "Comms Agent generated personalized advisories, queued to database"
- "Schedule Agent created follow-up calls for high-risk clients"
- "Filesystem MCP saved the advisory report as a file"
- "Memory MCP stored the event context for future reference"

Show audit trail:
```bash
curl -s https://YOUR-URL/workflows/WF-XXXX | python -m json.tool
```

## 1:30-2:15 — Pre-Call Brief

```bash
curl -s -X POST https://YOUR-URL/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Brief me on Priya Sharma before my call"}' \
  | python -m json.tool
```

- "360-degree brief from AlloyDB"
- "Memory MCP searched for past context on Priya"
- "Brief saved as markdown via Filesystem MCP"

## 2:15-2:45 — MCP Tools Showcase

```bash
curl -s https://YOUR-URL/tools | python -m json.tool
curl -s https://YOUR-URL/mcp/status | python -m json.tool
```

- "25 tools across 7 modules — 3 MCP servers running: Fetch, Memory, Filesystem"
- "All zero-config, no API keys, no OAuth — just npx"

## 2:45-3:00 — Wrap

"Pure Google stack: ADK, Gemini, AlloyDB, Cloud Run. MCP protocol for tool integration. Balanced architecture: database for persistence, MCP for context and content, Gemini for intelligence. Thank you."
