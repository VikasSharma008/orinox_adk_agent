# ORINOX v2 — Gmail & Calendar MCP Setup Guide

## Overview

ORINOX v2 uses two MCP integrations:
1. **Gmail MCP** — send advisory emails, search past threads, create drafts
2. **Google Calendar MCP** — schedule follow-up calls, find free slots, manage events

Both are provided by the **Google Workspace MCP Server** — one server, both services.

---

## Option 1: Google Workspace MCP Server (Recommended)

The open-source Google Workspace MCP Server (workspacemcp.com) covers Gmail + Calendar + 10 more services in one server.

### Install

```bash
# Clone
git clone https://github.com/gongrzhe/google-workspace-mcp-server.git
cd google-workspace-mcp-server

# Install
npm install

# Configure OAuth
cp .env.example .env
```

### OAuth Setup

1. Go to Google Cloud Console → APIs & Services → Credentials
2. Create OAuth 2.0 Client ID (Desktop App or Web App)
3. Enable Gmail API and Google Calendar API
4. Download credentials.json
5. Update .env:

```
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:3000/oauth/callback
```

### Run

```bash
# Start Gmail MCP on port 3000
npm start -- --services gmail --port 3000

# In another terminal, start Calendar MCP on port 3001
npm start -- --services calendar --port 3001
```

### Connect to ORINOX

Update your `.env`:

```bash
GMAIL_MCP_SERVER_URL=http://localhost:3000/sse
GMAIL_ENABLED=true
CALENDAR_MCP_SERVER_URL=http://localhost:3001/sse
CALENDAR_ENABLED=true
```

---

## Option 2: Composio MCP Tool Router

Composio handles OAuth, token refresh, and scopes automatically.

1. Sign up at composio.dev
2. Create a Gmail + Calendar integration
3. Get your MCP server URL
4. Set in .env:

```bash
GMAIL_MCP_SERVER_URL=https://mcp.composio.dev/gmail/your-key
GMAIL_ENABLED=true
CALENDAR_MCP_SERVER_URL=https://mcp.composio.dev/googlecalendar/your-key
CALENDAR_ENABLED=true
```

---

## Option 3: Run Without MCP (Demo Fallback)

ORINOX works without Gmail/Calendar MCP connected. When MCP is unavailable:

- **Emails**: Queued in AlloyDB `communications` table with status "queued"
- **Calendar events**: Stored in AlloyDB `scheduled_events` table
- **All agent logic runs normally** — only delivery channel changes

This is the default behavior when `GMAIL_ENABLED=false` and `CALENDAR_ENABLED=false`.

The demo still shows: market analysis, client segmentation, message generation, workflow audit trail. The only difference is emails don't physically arrive and calendar events don't physically appear.

---

## Gmail MCP Tools Used by ORINOX

| Tool | What It Does | When Called |
|------|-------------|------------|
| gmail_send_email | Send email to client | After generating advisory |
| gmail_draft_email | Create draft for RM review | Pre-call brief attachment |
| gmail_search_emails | Search past threads | Pre-call brief context |
| gmail_get_thread | Get full thread | Follow-up context |

## Calendar MCP Tools Used by ORINOX

| Tool | What It Does | When Called |
|------|-------------|------------|
| calendar_create_event | Schedule a call | After market event segmentation |
| calendar_list_events | Check RM schedule | Before scheduling |
| calendar_find_free_slots | Find available times | Batch scheduling |
| calendar_schedule_batch_followups | Bulk create events | Market event workflow |
| calendar_update_event | Reschedule | On request |
| calendar_delete_event | Cancel | On request |

---

## Testing Checklist

| # | Test | Expected |
|---|------|----------|
| 1 | Health check | `gmail_mcp: enabled, calendar_mcp: enabled` |
| 2 | Send test email | Email arrives in recipient inbox |
| 3 | Search emails | Returns recent threads |
| 4 | Create calendar event | Event appears on Google Calendar |
| 5 | Find free slots | Returns available times |
| 6 | Hero demo /chat | Emails sent + events created + audit logged |

---

## ADK McpToolset Integration (Future)

For native ADK integration (instead of HTTP calls), use:

```python
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset, SseConnectionParams

gmail_tools = McpToolset(
    connection_params=SseConnectionParams(url="http://localhost:3000/sse")
)

calendar_tools = McpToolset(
    connection_params=SseConnectionParams(url="http://localhost:3001/sse")
)

agent = LlmAgent(
    model="gemini-1.5-flash",
    tools=[gmail_tools, calendar_tools]
)
```

This replaces the HTTP-based tool calls in `gmail_tools.py` and `calendar_tools.py` with native ADK MCP client integration.
