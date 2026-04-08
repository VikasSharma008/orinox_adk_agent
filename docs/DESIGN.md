# ORINOX v2 — Design Thinking, Architecture & Approach

## Gen AI Academy APAC Hackathon 2025

---

## 1. Problem Statement

Relationship Managers (RMs) in wealth management face a critical productivity crisis:

- **Research overload**: Market analysis requires manual effort across fragmented data sources. Real-time advice is impossible at scale.
- **Manual outreach**: Personalizing communications to 450+ clients is a manual, error-prone process that is rarely performed in real time.
- **Information silos**: Client data (family, work, demographics, portfolios) scattered across systems. No single 360-degree view before a call.
- **Scheduling chaos**: Coordinating client calls, follow-ups, and team meetings across calendars is manual and slow.

**Persona**: Vikram — Relationship Manager for mass affluent wealth segment in Mumbai. 450 client relationships. Needs his CRM to act as an intelligent co-pilot.

---

## 2. Our Solution: ORINOX

An AI-powered multi-agent orchestration system that empowers RMs to:

1. **React to market events instantly** — auto-segment impacted clients, generate personalized advisories
2. **Prepare for calls in seconds** — 360-degree client briefs assembled from structured data
3. **Communicate at scale** — personalized emails drafted and sent via Gmail
4. **Manage schedules intelligently** — auto-schedule client follow-ups on Google Calendar
5. **Collaborate with research teams** — email-based research queries with tracking

### Elevator Pitch

> A single conversational interface where an RM says "RBI hiked rates — who's exposed and what should I tell them?" and the system segments 62 of 450 clients, generates personalized advisory emails, sends them via Gmail, schedules follow-up calls on Calendar — all in under 30 seconds.

---

## 3. Architecture

### 3.1 Agent Topology

```
User (Vikram the RM)
        │
        ▼
┌──────────────────────────┐
│   ORCHESTRATOR AGENT     │  Google ADK + Gemini
│   (Primary Agent)        │  Intent parsing, step planning, routing
└──┬────┬──────┬──────┬───┘
   │    │      │      │
   ▼    ▼      ▼      ▼
┌──────┐┌──────┐┌──────┐┌──────┐
│Market││Client││Comms ││Sched │
│Agent ││Brief ││Agent ││Agent │
│      ││Agent ││      ││      │
└──┬───┘└──┬───┘└──┬───┘└──┬───┘
   │       │       │       │
   ▼       ▼       ▼       ▼
yfinance AlloyDB  Gmail   Google
+Search  Client   MCP    Calendar
Grounding Data   Server  MCP Server
   │       │       │       │
   └───────┴───┬───┴───────┘
               ▼
           AlloyDB
       (PostgreSQL)
    Structured + Vector
```

### 3.2 Component Breakdown

#### Orchestrator Agent (Primary)
- **Tech**: Google ADK + Gemini 1.5 Pro
- **Role**: Receives natural language from RM, decomposes into a multi-step plan, routes to sub-agents in sequence, aggregates results
- **Routing logic**: Intent classification → agent selection → execution plan → sequential dispatch → response assembly

#### Market Monitor Agent
- **Tech**: Gemini + yfinance + Gemini search grounding
- **Role**: Analyze market events, identify sector/instrument impact, assess severity
- **Tools**: market_search, market_get_stock_data, market_analyze_impact

#### Client Brief Agent
- **Tech**: Gemini + AlloyDB direct queries
- **Role**: Pull 360-degree client data, segment clients by exposure, generate pre-call briefs
- **Tools**: client_get_profile, client_get_portfolio, client_get_household, client_get_interactions, client_segment_by_criteria, client_get_360
- **Vector Search**: Gemini text embeddings + pgvector for semantic client-to-event matching

#### Communication Agent
- **Tech**: Gemini + Gmail MCP Server
- **Role**: Generate personalized emails, send via Gmail, log all communications
- **MCP Tools**: gmail_send_email, gmail_draft_email, gmail_search_emails, gmail_get_thread
- **Internal Tools**: comms_generate_advisory, comms_generate_batch, comms_send_and_log

#### Scheduling Agent
- **Tech**: Gemini + Google Calendar MCP Server
- **Role**: Schedule client calls, find free slots, batch follow-ups, manage RM calendar
- **MCP Tools**: calendar_create_event, calendar_list_events, calendar_find_free_slots, calendar_schedule_batch_followups, calendar_update_event, calendar_delete_event

### 3.3 Data Layer — AlloyDB

All client data lives in AlloyDB (replaces Salesforce FSC).

**Tables**: clients, portfolios, households, market_events, client_segments, communications, scheduled_events, interactions, workflow_logs

### 3.4 MCP Integration

**Google Workspace MCP Server** (workspacemcp.com) — single open-source server covering Gmail + Calendar, OAuth 2.1.

ADK agents connect via McpToolset with SseConnectionParams.

---

## 4. Demo Scenarios

### Scenario 1: Market Event Response (Hero Demo)
*"RBI just hiked rates by 50bps. Who in my book is exposed and what should I tell them?"*

1. Market Agent → analyzes impact
2. Client Brief Agent → segments 62/450 clients
3. Comms Agent → generates emails → sends via Gmail MCP
4. Schedule Agent → creates follow-up calls on Google Calendar
5. All logged to workflow_logs

### Scenario 2: Pre-Call Brief
*"I have a call with Priya Sharma in 10 minutes. Brief me."*

1. Client Brief Agent → 360-degree view from AlloyDB
2. Market Agent → checks recent events against her portfolio
3. Comms Agent → searches Gmail for recent thread with Priya

### Scenario 3: Schedule and Notify
*"Schedule portfolio review calls with all my high-risk clients next week"*

1. Client Brief Agent → queries high-risk clients
2. Schedule Agent → finds free slots → creates calendar events
3. Comms Agent → sends confirmation emails via Gmail

### Scenario 4: Research Query
*"Email the research desk about IT sector outlook given tariff news"*

1. Comms Agent → drafts and sends email via Gmail MCP
2. Logs tracking ID to AlloyDB

---

## 5. Technology Stack

| Component | Technology | Cost |
|-----------|-----------|------|
| Orchestrator | Google ADK + Gemini API | Free tier |
| Market Data | yfinance + Gemini search grounding | Free |
| Client Data | AlloyDB (PostgreSQL) | Hackathon credits |
| Vector Search | AlloyDB pgvector + Gemini embeddings | Hackathon credits |
| Email | Gmail MCP Server | Free (OAuth) |
| Calendar | Google Calendar MCP Server | Free (OAuth) |
| API Framework | FastAPI + Uvicorn | Free |
| Deployment | Google Cloud Run | Hackathon credits |

**Total additional cost: $0**

---

## 6. What Makes This Win

1. **Real-world workflow** — actual RM workflow end-to-end
2. **Multi-agent coordination visible** — orchestrator reasoning exposed in API
3. **MCP used correctly** — Gmail + Calendar via standard MCP protocol
4. **Google-native stack** — ADK + Gemini + AlloyDB + Cloud Run + Gmail + Calendar
5. **Multi-step workflow** — one message triggers 4 agent actions
6. **Vector search** — semantic client matching via pgvector
7. **Real delivery** — emails arrive, calendar events appear, nothing simulated
