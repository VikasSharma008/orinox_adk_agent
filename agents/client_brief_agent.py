"""ORINOX v3 Client Brief Agent — AlloyDB direct queries, segmentation, pre-call briefs"""
import json, time
from config import generate_content
from tools.registry import get_registry
from db.database import get_db


class ClientBriefAgent:
    name = "CLIENT_BRIEF_AGENT"

    async def execute(self, action, params, workflow_id=None, step=0):
        reg, db = get_registry(), await get_db()
        start = time.time()
        if workflow_id:
            await db.log_step(workflow_id, step, self.name, action,
                              input_summary=json.dumps(params)[:500], status="running")
        try:
            result = await self._route(action, params, reg)
            ms = int((time.time() - start) * 1000)
            if workflow_id:
                await db.log_step(workflow_id, step, self.name, action,
                    output_summary=json.dumps(result, default=str)[:500],
                    status="completed", duration_ms=ms)
            return {"agent": self.name, "action": action, "result": result, "duration_ms": ms}
        except Exception as e:
            if workflow_id:
                await db.log_step(workflow_id, step, self.name, action,
                                  status="failed", error_message=str(e))
            return {"agent": self.name, "action": action, "error": str(e)}

    async def _route(self, action, params, reg):
        if action in ("get_360", "pre_call_brief", "client_get_360"):
            return await reg.call("client_get_360",
                client_id=params.get("client_id"), client_name=params.get("client_name"))
        elif action in ("segment", "client_segment_by_criteria"):
            return await reg.call("client_segment_by_criteria",
                sector=params.get("sector"), instrument_type=params.get("instrument_type"),
                risk_profile=params.get("risk_profile"), min_aum=params.get("min_aum"))
        elif action in ("get_profile", "client_get_profile"):
            return await reg.call("client_get_profile",
                client_name=params.get("client_name"), client_id=params.get("client_id"))
        elif action in ("get_portfolio", "client_get_portfolio"):
            return await reg.call("client_get_portfolio", client_id=params.get("client_id"))
        return {"error": f"Unknown action: {action}"}

    async def segment_by_market_impact(self, market_analysis, workflow_id=None, step=0):
        reg, db = get_registry(), await get_db()
        sector_impacts = market_analysis.get("sector_impacts", [])
        instrument_impacts = market_analysis.get("instrument_impacts", [])
        event_id = market_analysis.get("event_id")

        all_exposed, seen = [], set()

        for si in sector_impacts:
            if si.get("direction") == "negative" or si.get("magnitude") in ("medium", "high"):
                seg = await reg.call("client_segment_by_criteria", sector=si["sector"])
                for c in seg.get("clients", []):
                    if c["id"] not in seen:
                        seen.add(c["id"])
                        c["exposure_sector"] = si["sector"]
                        c["impact_direction"] = si.get("direction", "negative")
                        c["impact_magnitude"] = si.get("magnitude", "medium")
                        all_exposed.append(c)
                        if event_id:
                            await db.create_segment({
                                "event_id": event_id, "client_id": c["id"],
                                "exposure_type": f"sector:{si['sector']}",
                                "exposure_amount": c.get("current_value", 0),
                                "risk_level": si.get("magnitude", "medium"),
                                "segment_label": f"{si['sector']}_{si.get('direction', 'neg')}"})

        for ii in instrument_impacts:
            if ii.get("direction") == "negative" or ii.get("magnitude") in ("medium", "high"):
                seg = await reg.call("client_segment_by_criteria", instrument_type=ii["type"])
                for c in seg.get("clients", []):
                    if c["id"] not in seen:
                        seen.add(c["id"])
                        c["exposure_type"] = ii["type"]
                        c["impact_direction"] = ii.get("direction", "negative")
                        c["impact_magnitude"] = ii.get("magnitude", "medium")
                        all_exposed.append(c)

        high = [c for c in all_exposed if c.get("impact_magnitude") == "high"]
        med = [c for c in all_exposed if c.get("impact_magnitude") == "medium"]
        low = [c for c in all_exposed if c.get("impact_magnitude") == "low"]

        result = {"total_exposed": len(all_exposed),
                  "segments": {"high_risk": {"count": len(high), "clients": high},
                               "medium_risk": {"count": len(med), "clients": med},
                               "low_risk": {"count": len(low), "clients": low}},
                  "event_id": event_id}

        if workflow_id:
            await db.log_step(workflow_id, step, self.name, "segment_by_market_impact",
                output_summary=f"{len(all_exposed)} exposed: {len(high)} high, {len(med)} med, {len(low)} low",
                status="completed")
        return result

    async def generate_pre_call_brief(self, client_name=None, client_id=None):
        reg = get_registry()
        raw = await reg.call("client_get_360", client_id=client_id, client_name=client_name)
        if "error" in raw:
            return raw
        try:
            prompt = f"""Format this into a concise pre-call brief for a Relationship Manager.

{json.dumps(raw, indent=2, default=str)[:3000]}

Sections: 1) Client Summary 2) Portfolio Snapshot 3) Family 4) Recent Interactions 5) Talking Points
Keep it concise — quick reference, not a report."""
            brief_text = generate_content(prompt)
            return {"client_name": client_name or raw.get("profile", {}).get("name"),
                    "brief": brief_text, "raw_data": raw}
        except Exception as e:
            return {"client_name": client_name, "raw_data": raw, "brief_error": str(e)}
