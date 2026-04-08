"""ORINOX v3 Orchestrator — Primary agent with intent routing, MCP integration, workflow execution"""
import json, time, uuid
from datetime import datetime, timedelta
from config import generate_content
from agents.market_agent import MarketAgent
from agents.client_brief_agent import ClientBriefAgent
from agents.comms_agent import CommsAgent
from agents.schedule_agent import ScheduleAgent
from agents.prompts import ORCHESTRATOR_PROMPT
from db.database import get_db


class Orchestrator:
    def __init__(self):
        self.name = "ORCHESTRATOR"
        self.market = MarketAgent()
        self.client_brief = ClientBriefAgent()
        self.comms = CommsAgent()
        self.schedule = ScheduleAgent()

    async def process(self, user_message: str) -> dict:
        """Main entry: natural language -> multi-agent workflow -> structured response."""
        wf_id = f"WF-{uuid.uuid4().hex[:8]}"
        db = await get_db()
        start = time.time()

        plan = await self._create_plan(user_message)
        await db.log_step(wf_id, 0, self.name, "create_plan",
                          input_summary=user_message[:500],
                          output_summary=json.dumps(plan)[:500], status="completed")

        intent = plan.get("intent", "general_query")
        if intent == "market_event_response":
            results = await self._wf_market_event(user_message, plan, wf_id)
        elif intent == "pre_call_brief":
            results = await self._wf_pre_call_brief(user_message, plan, wf_id)
        elif intent == "schedule_followups":
            results = await self._wf_schedule_followups(user_message, plan, wf_id)
        elif intent == "research_query":
            results = await self._wf_research_query(user_message, plan, wf_id)
        else:
            results = await self._wf_generic(plan, wf_id)

        duration = int((time.time() - start) * 1000)
        summary = await self._summarize(user_message, results, intent)
        await db.log_step(wf_id, 99, self.name, "complete",
                          output_summary=summary[:500], status="completed", duration_ms=duration)

        return {"workflow_id": wf_id, "intent": intent, "plan": plan,
                "results": results, "summary": summary, "total_duration_ms": duration}

    async def _create_plan(self, msg):
        try:
            prompt = f"{ORCHESTRATOR_PROMPT}\n\nUser message: \"{msg}\"\n\nCreate the execution plan JSON."
            text = generate_content(prompt)
            t = text.strip()
            if "```json" in t: t = t.split("```json")[1].split("```")[0].strip()
            elif "```" in t: t = t.split("```")[1].split("```")[0].strip()
            return json.loads(t)
        except:
            return self._fallback_plan(msg)

    def _fallback_plan(self, msg):
        m = msg.lower()
        if any(w in m for w in ["rate", "hike", "cut", "rbi", "fed", "market", "crash",
                                 "tariff", "impact", "exposed", "sector"]):
            return {"intent": "market_event_response",
                    "plan": [{"step":1,"agent":"MARKET_AGENT","action":"analyze_event","params":{"event_description":msg}},
                             {"step":2,"agent":"CLIENT_BRIEF_AGENT","action":"segment"},
                             {"step":3,"agent":"COMMS_AGENT","action":"email_segment"},
                             {"step":4,"agent":"SCHEDULE_AGENT","action":"batch_followups"}],
                    "reasoning": "Market event detected"}
        elif any(w in m for w in ["brief", "call", "meeting", "prepare", "tell me about"]):
            return {"intent": "pre_call_brief",
                    "plan": [{"step":1,"agent":"CLIENT_BRIEF_AGENT","action":"pre_call_brief","params":{"client_name":msg}}],
                    "reasoning": "Pre-call brief request"}
        elif any(w in m for w in ["schedule", "calendar", "book", "follow-up", "followup", "next week"]):
            return {"intent": "schedule_followups",
                    "plan": [{"step":1,"agent":"CLIENT_BRIEF_AGENT","action":"segment"},
                             {"step":2,"agent":"SCHEDULE_AGENT","action":"batch_followups"},
                             {"step":3,"agent":"COMMS_AGENT","action":"send_confirmations"}],
                    "reasoning": "Scheduling request"}
        elif any(w in m for w in ["research", "ask", "desk", "team", "query", "email the"]):
            return {"intent": "research_query",
                    "plan": [{"step":1,"agent":"COMMS_AGENT","action":"send_research_query","params":{"query":msg}}],
                    "reasoning": "Research query via email"}
        return {"intent": "general_query", "plan": [], "reasoning": "Unclassified"}

    # ─── Workflow: Market Event Response ───

    async def _wf_market_event(self, msg, plan, wf_id):
        results = []

        r1 = await self.market.execute("analyze_event", {"event_description": msg}, wf_id, 1)
        results.append(r1)
        analysis = r1.get("result", {})
        if "error" in analysis:
            return results

        seg = await self.client_brief.segment_by_market_impact(analysis, wf_id, 2)
        all_clients, high_risk_clients = [], []
        for level in ["high_risk", "medium_risk", "low_risk"]:
            clients = seg.get("segments", {}).get(level, {}).get("clients", [])
            all_clients.extend(clients)
            if level == "high_risk":
                high_risk_clients = clients

        results.append({"agent": "CLIENT_BRIEF_AGENT", "action": "segment_by_market_impact",
                        "result": {"total_exposed": seg.get("total_exposed", 0),
                                   "segments": {k: v.get("count", 0) for k, v in seg.get("segments", {}).items()},
                                   "event_id": seg.get("event_id")}})

        if not all_clients:
            return results

        event_summary = analysis.get("impact_analysis", analysis.get("event_title", msg))
        email_result = await self.comms.email_segment(
            all_clients, event_summary,
            event_id=analysis.get("event_id"), workflow_id=wf_id, step=3)
        results.append({"agent": "COMMS_AGENT", "action": "email_segment", "result": email_result})

        if high_risk_clients:
            tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
            sched_result = await self.schedule.schedule_followups_for_segment(
                high_risk_clients, tomorrow, workflow_id=wf_id, step=4)
            results.append({"agent": "SCHEDULE_AGENT", "action": "schedule_followups", "result": sched_result})

        # MCP: Save advisory report via Filesystem MCP
        from tools.registry import get_registry
        reg = get_registry()
        report = await reg.call("fs_save_advisory_report",
            event_title=analysis.get("event_title", msg[:50]),
            clients_count=len(all_clients),
            messages_summary=email_result.get("messages", [])[:20],
            workflow_id=wf_id)
        results.append({"agent": "FILESYSTEM_MCP", "action": "save_report", "result": report})

        # MCP: Store event context in Memory MCP
        await reg.call("memory_store_entity",
            entity_name=analysis.get("event_title", msg[:50]),
            entity_type="market_event",
            observations=[
                f"Severity: {analysis.get('risk_level', 'medium')}",
                f"Clients impacted: {len(all_clients)}",
                f"Sectors: {', '.join(s.get('sector','') for s in analysis.get('sector_impacts',[]))}",
                f"Workflow: {wf_id}",
            ])

        return results

    # ─── Workflow: Pre-Call Brief ───

    async def _wf_pre_call_brief(self, msg, plan, wf_id):
        results = []
        params = plan.get("plan", [{}])[0].get("params", {}) if plan.get("plan") else {}
        client_name = params.get("client_name", msg)

        brief = await self.client_brief.generate_pre_call_brief(client_name=client_name)
        results.append({"agent": "CLIENT_BRIEF_AGENT", "action": "pre_call_brief", "result": brief})

        from tools.registry import get_registry
        reg = get_registry()
        if brief.get("client_name"):
            memory_result = await reg.call("memory_search", query=brief["client_name"])
            results.append({"agent": "MEMORY_MCP", "action": "search_context", "result": memory_result})

            profile = brief.get("raw_data", {}).get("profile", {})
            await reg.call("memory_store_client_context",
                client_name=brief["client_name"],
                context={"risk_profile": profile.get("risk_profile"),
                         "last_advisory": "pre_call_brief generated",
                         "notes": f"Brief generated for workflow {wf_id}"})

            if brief.get("brief"):
                save_result = await reg.call("fs_save_brief",
                    client_name=brief["client_name"],
                    brief_content=brief["brief"], workflow_id=wf_id)
                results.append({"agent": "FILESYSTEM_MCP", "action": "save_brief", "result": save_result})

        return results

    # ─── Workflow: Schedule Follow-ups ───

    async def _wf_schedule_followups(self, msg, plan, wf_id):
        results = []
        seg = await self.client_brief.execute("segment", {"risk_profile": "aggressive"}, wf_id, 1)
        results.append(seg)

        clients = seg.get("result", {}).get("clients", [])
        if not clients:
            return results

        next_monday = datetime.now()
        while next_monday.weekday() != 0:
            next_monday += timedelta(days=1)
        date_start = next_monday.strftime("%Y-%m-%d")

        sched = await self.schedule.schedule_followups_for_segment(
            clients, date_start, workflow_id=wf_id, step=2)
        results.append({"agent": "SCHEDULE_AGENT", "action": "batch_followups", "result": sched})

        for client in clients[:10]:
            await self.comms.execute("queue_and_log", {
                "client": client,
                "subject": "Upcoming Portfolio Review Call",
                "body": f"Dear {client.get('name','')},\n\nA portfolio review call has been scheduled for you.\n\nBest regards,\nVikram",
                "workflow_id": wf_id
            }, wf_id, 3)

        results.append({"agent": "COMMS_AGENT", "action": "send_confirmations",
                        "result": {"sent": min(len(clients), 10)}})
        return results

    # ─── Workflow: Research Query ───

    async def _wf_research_query(self, msg, plan, wf_id):
        results = []
        params = plan.get("plan", [{}])[0].get("params", {}) if plan.get("plan") else {}
        query = params.get("query", msg)
        result = await self.comms.send_research_query(query, workflow_id=wf_id, step=1)
        results.append({"agent": "COMMS_AGENT", "action": "send_research_query", "result": result})
        return results

    # ─── Generic ───

    async def _wf_generic(self, plan, wf_id):
        results = []
        agents = {"MARKET_AGENT": self.market, "CLIENT_BRIEF_AGENT": self.client_brief,
                  "COMMS_AGENT": self.comms, "SCHEDULE_AGENT": self.schedule}
        for s in plan.get("plan", []):
            agent = agents.get(s.get("agent"))
            if agent:
                r = await agent.execute(s.get("action",""), s.get("params",{}), wf_id, s.get("step",0))
                results.append(r)
        return results

    # ─── Summary ───

    async def _summarize(self, msg, results, intent):
        try:
            prompt = f"""Summarize for an RM. Be concise and actionable. Plain text, no markdown.
Request: "{msg}"
Intent: {intent}
Results: {json.dumps(results, default=str)[:3000]}
Write 3-5 sentences."""
            return generate_content(prompt).strip()
        except:
            if intent == "market_event_response":
                return "Market event analyzed. Impacted clients identified, advisory messages queued, and follow-up calls scheduled."
            elif intent == "pre_call_brief":
                return "Pre-call brief generated with 360-degree client view."
            elif intent == "schedule_followups":
                return "Follow-up calls scheduled. Confirmation messages sent."
            elif intent == "research_query":
                return "Research query sent to the research desk."
            return "Workflow completed."
