"""ORINOX v2 Scheduling Agent — Google Calendar MCP for event management"""
import json, time
from tools.registry import get_registry
from db.database import get_db


class ScheduleAgent:
    name = "SCHEDULE_AGENT"

    async def execute(self, action, params, workflow_id=None, step=0):
        reg, db = get_registry(), await get_db()
        start = time.time()
        if workflow_id:
            await db.log_step(workflow_id, step, self.name, action,
                              input_summary=json.dumps(params, default=str)[:500], status="running")
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
        if action in ("create_event", "calendar_create_event"):
            return await reg.call("calendar_create_event", **params)
        elif action in ("list_events", "calendar_list_events"):
            return await reg.call("calendar_list_events", **params)
        elif action in ("find_free_slots", "calendar_find_free_slots"):
            return await reg.call("calendar_find_free_slots", **params)
        elif action in ("batch_followups", "calendar_schedule_batch_followups"):
            return await reg.call("calendar_schedule_batch_followups", **params)
        elif action in ("update_event", "calendar_update_event"):
            return await reg.call("calendar_update_event", **params)
        elif action in ("delete_event", "calendar_delete_event"):
            return await reg.call("calendar_delete_event", **params)
        return {"error": f"Unknown action: {action}"}

    async def schedule_followups_for_segment(self, clients, date_start,
                                              workflow_id=None, step=0):
        """Schedule follow-up calls for impacted clients after a market event."""
        reg, db = get_registry(), await get_db()
        result = await reg.call("calendar_schedule_batch_followups",
            clients=clients, date_start=date_start,
            title_template="Portfolio Review: {client_name}",
            duration_minutes=30, workflow_id=workflow_id)
        if workflow_id:
            await db.log_step(workflow_id, step, self.name, "schedule_followups_for_segment",
                output_summary=f"Scheduled {result.get('total_scheduled', 0)} follow-up calls",
                status="completed")
        return result
