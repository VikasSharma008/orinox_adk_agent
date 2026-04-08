# ORINOX v2 API Reference

Base URL: `https://your-cloud-run-url`

---

## POST /chat — Main Entry Point

Natural language → multi-agent workflow → structured response.

```bash
curl -X POST /chat -H "Content-Type: application/json" \
  -d '{"message": "RBI hiked rates by 50bps. Who is exposed?"}'
```

Response:
```json
{
  "workflow_id": "WF-a1b2c3d4",
  "intent": "market_event_response",
  "summary": "Analyzed rate hike. Found 8 exposed clients. Sent advisory emails. Scheduled 3 follow-up calls.",
  "results": [...],
  "plan": {...},
  "total_duration_ms": 6200
}
```

---

## POST /workflow — Direct Workflow Execution

```bash
curl -X POST /workflow -H "Content-Type: application/json" \
  -d '{"intent": "pre_call_brief", "params": {"client_name": "Priya Sharma"}}'
```

Supported intents: `market_event_response`, `pre_call_brief`, `schedule_followups`, `research_query`

---

## GET /clients

List clients. Optional filters: `?segment=mass_affluent&risk=aggressive&limit=20`

## GET /clients/{id}

Single client profile.

## GET /clients/{id}/brief

Gemini-generated 360-degree pre-call brief.

## GET /clients/{id}/portfolio

Financial holdings with total value.

## GET /clients/{id}/household

Family members and dependents.

---

## GET /events

Market events logged by Market Agent.

## GET /communications

Email log. Filter: `?workflow_id=WF-xxx&status=sent`

## GET /schedule

Calendar events. Filter: `?workflow_id=WF-xxx`

## GET /workflows/{id}

Full audit trail — every agent step, timing, inputs, outputs.

## GET /tools

All 22 registered MCP tools with schemas.

## GET /health

Status, agents, tool count, Gmail/Calendar MCP connectivity.
