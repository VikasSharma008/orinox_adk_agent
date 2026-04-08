"""ORINOX v2 Market Monitor Agent"""
import json, time
from tools.registry import get_registry
from db.database import get_db

class MarketAgent:
    name = "MARKET_AGENT"

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
        if action in ("analyze_event", "market_analyze_impact"):
            return await reg.call("market_analyze_impact",
                event_description=params.get("event_description", params.get("query", "")),
                sectors=params.get("sectors"))
        elif action in ("search", "market_search"):
            return await reg.call("market_search", query=params.get("query", ""))
        elif action in ("get_stock", "market_get_stock_data"):
            return await reg.call("market_get_stock_data",
                symbol=params.get("symbol", ""), period=params.get("period", "1mo"))
        return {"error": f"Unknown action: {action}"}
