"""ORINOX v3 Database Manager — AlloyDB (prod) / SQLite (dev) dual backend"""
import os, json, uuid, aiosqlite
from pathlib import Path

SCHEMA_PATH = Path(__file__).parent / "schema.sql"
_inst = None

USE_SQLITE = os.getenv("USE_SQLITE", "true").lower() == "true"

def _id():
    return uuid.uuid4().hex[:12]


class DatabaseManager:
    def __init__(self):
        self._sqlite_path = os.getenv("SQLITE_PATH", "orinox_dev.db")
        self._pg_pool = None
        self._ready = False

    async def init(self):
        if self._ready:
            return
        if USE_SQLITE:
            db = await aiosqlite.connect(self._sqlite_path)
            await db.executescript(SCHEMA_PATH.read_text())
            await db.commit()
            await db.close()
        else:
            import asyncpg
            self._pg_pool = await asyncpg.create_pool(
                host=os.getenv("ALLOYDB_HOST"),
                port=int(os.getenv("ALLOYDB_PORT", "5432")),
                user=os.getenv("ALLOYDB_USER", "postgres"),
                password=os.getenv("ALLOYDB_PASSWORD"),
                database=os.getenv("ALLOYDB_DATABASE", "orinox"),
                min_size=1,
                max_size=5,
            )
            # Run schema — PostgreSQL version
            schema_sql = SCHEMA_PATH.read_text()
            schema_pg = schema_sql.replace("datetime('now')", "NOW()")
            async with self._pg_pool.acquire() as conn:
                # Execute each statement separately (asyncpg doesn't support executescript)
                for stmt in schema_pg.split(";"):
                    stmt = stmt.strip()
                    if stmt:
                        try:
                            await conn.execute(stmt)
                        except Exception:
                            pass  # IF NOT EXISTS handles duplicates
        self._ready = True

    # ── Connection helpers ──

    async def _conn(self):
        """Return SQLite connection (only used in SQLite mode)."""
        c = await aiosqlite.connect(self._sqlite_path)
        c.row_factory = aiosqlite.Row
        await c.execute("PRAGMA journal_mode=WAL")
        await c.execute("PRAGMA foreign_keys=ON")
        return c

    async def _q(self, sql, params=()):
        """Query — returns list of dicts. Handles both SQLite (?) and PostgreSQL ($N)."""
        if USE_SQLITE:
            c = await self._conn()
            try:
                cur = await c.execute(sql, params)
                if sql.strip().upper().startswith("SELECT"):
                    return [dict(r) for r in await cur.fetchall()]
                await c.commit()
                return [{"lastrowid": cur.lastrowid}]
            finally:
                await c.close()
        else:
            pg_sql, pg_params = self._to_pg(sql, params)
            async with self._pg_pool.acquire() as conn:
                if pg_sql.strip().upper().startswith("SELECT"):
                    rows = await conn.fetch(pg_sql, *pg_params)
                    return [dict(r) for r in rows]
                await conn.execute(pg_sql, *pg_params)
                return [{"status": "ok"}]

    async def _w(self, sql, params=()):
        """Write — execute and commit."""
        if USE_SQLITE:
            c = await self._conn()
            try:
                await c.execute(sql, params)
                await c.commit()
            finally:
                await c.close()
        else:
            pg_sql, pg_params = self._to_pg(sql, params)
            async with self._pg_pool.acquire() as conn:
                await conn.execute(pg_sql, *pg_params)

    @staticmethod
    def _to_pg(sql, params):
        """Convert SQLite ? placeholders to PostgreSQL $1,$2,... and datetime('now') to NOW()."""
        pg_sql = sql.replace("datetime('now')", "NOW()")
        # Replace ? with $1, $2, ...
        parts = pg_sql.split("?")
        if len(parts) > 1:
            pg_sql = ""
            for i, part in enumerate(parts[:-1]):
                pg_sql += part + f"${i+1}"
            pg_sql += parts[-1]
        return pg_sql, list(params)

    # ── Clients ──
    async def get_client(self, cid):
        r = await self._q("SELECT * FROM clients WHERE id=?", (cid,))
        return r[0] if r else None

    async def find_client(self, name):
        r = await self._q("SELECT * FROM clients WHERE LOWER(name) LIKE LOWER(?)", (f"%{name}%",))
        return r[0] if r else None

    async def list_clients(self, segment=None, risk=None, limit=100):
        sql, p = "SELECT * FROM clients WHERE 1=1", []
        if segment: sql += " AND segment=?"; p.append(segment)
        if risk: sql += " AND risk_profile=?"; p.append(risk)
        sql += " ORDER BY name LIMIT ?"; p.append(limit)
        return await self._q(sql, tuple(p))

    async def upsert_client(self, d):
        cid = d.get("id") or _id()
        if USE_SQLITE:
            await self._w(
                """INSERT INTO clients(id,name,email,phone,segment,risk_profile,
                   channel_preference,occupation,city,region,date_of_birth,aum)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(id) DO UPDATE SET name=excluded.name,email=excluded.email,
                   aum=excluded.aum,updated_at=datetime('now')""",
                (cid, d["name"], d.get("email"), d.get("phone"),
                 d.get("segment","mass_affluent"), d.get("risk_profile","moderate"),
                 d.get("channel_preference","email"), d.get("occupation"),
                 d.get("city"), d.get("region","west"), d.get("date_of_birth"),
                 d.get("aum",0)))
        else:
            await self._w(
                """INSERT INTO clients(id,name,email,phone,segment,risk_profile,
                   channel_preference,occupation,city,region,date_of_birth,aum)
                   VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)
                   ON CONFLICT(id) DO UPDATE SET name=EXCLUDED.name,email=EXCLUDED.email,
                   aum=EXCLUDED.aum,updated_at=NOW()""",
                (cid, d["name"], d.get("email"), d.get("phone"),
                 d.get("segment","mass_affluent"), d.get("risk_profile","moderate"),
                 d.get("channel_preference","email"), d.get("occupation"),
                 d.get("city"), d.get("region","west"), d.get("date_of_birth"),
                 d.get("aum",0)))
        return {"id": cid, **d}

    # ── Portfolios ──
    async def get_portfolio(self, client_id):
        return await self._q(
            "SELECT * FROM portfolios WHERE client_id=? ORDER BY current_value DESC",
            (client_id,))

    async def get_clients_by_sector(self, sector):
        return await self._q(
            """SELECT DISTINCT c.*, p.instrument_name, p.instrument_type,
               p.sector, p.current_value, p.allocation_pct
               FROM clients c JOIN portfolios p ON c.id=p.client_id
               WHERE LOWER(p.sector) LIKE LOWER(?) ORDER BY p.current_value DESC""",
            (f"%{sector}%",))

    async def get_clients_by_instrument_type(self, itype):
        return await self._q(
            """SELECT DISTINCT c.*, p.instrument_name, p.instrument_type,
               p.sector, p.current_value, p.allocation_pct
               FROM clients c JOIN portfolios p ON c.id=p.client_id
               WHERE LOWER(p.instrument_type) LIKE LOWER(?) ORDER BY p.current_value DESC""",
            (f"%{itype}%",))

    async def upsert_portfolio(self, d):
        pid = d.get("id") or _id()
        if USE_SQLITE:
            await self._w(
                """INSERT INTO portfolios(id,client_id,instrument_name,instrument_type,
                   sector,quantity,avg_cost,current_value,allocation_pct,currency)
                   VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET
                   current_value=excluded.current_value,updated_at=datetime('now')""",
                (pid, d["client_id"], d["instrument_name"], d["instrument_type"],
                 d.get("sector"), d.get("quantity",0), d.get("avg_cost",0),
                 d.get("current_value",0), d.get("allocation_pct",0), d.get("currency","INR")))
        else:
            await self._w(
                """INSERT INTO portfolios(id,client_id,instrument_name,instrument_type,
                   sector,quantity,avg_cost,current_value,allocation_pct,currency)
                   VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10) ON CONFLICT(id) DO UPDATE SET
                   current_value=EXCLUDED.current_value,updated_at=NOW()""",
                (pid, d["client_id"], d["instrument_name"], d["instrument_type"],
                 d.get("sector"), d.get("quantity",0), d.get("avg_cost",0),
                 d.get("current_value",0), d.get("allocation_pct",0), d.get("currency","INR")))
        return {"id": pid, **d}

    # ── Households ──
    async def get_household(self, client_id):
        return await self._q("SELECT * FROM households WHERE client_id=?", (client_id,))

    async def add_household_member(self, d):
        mid = d.get("id") or _id()
        await self._w(
            "INSERT INTO households(id,client_id,member_name,relationship,date_of_birth,occupation,notes) VALUES(?,?,?,?,?,?,?)",
            (mid, d["client_id"], d["member_name"], d.get("relationship"),
             d.get("date_of_birth"), d.get("occupation"), d.get("notes")))
        return {"id": mid, **d}

    # ── Market Events ──
    async def create_market_event(self, d):
        eid = d.get("id") or _id()
        await self._w(
            """INSERT INTO market_events(id,title,description,event_type,severity,
               affected_sectors,affected_instruments,impact_analysis,source)
               VALUES(?,?,?,?,?,?,?,?,?)""",
            (eid, d["title"], d.get("description"), d.get("event_type"),
             d.get("severity","medium"), json.dumps(d.get("affected_sectors",[])),
             json.dumps(d.get("affected_instruments",[])),
             d.get("impact_analysis"), d.get("source")))
        return {"id": eid, **d}

    async def list_market_events(self, limit=20):
        return await self._q("SELECT * FROM market_events ORDER BY created_at DESC LIMIT ?", (limit,))

    # ── Segments ──
    async def create_segment(self, d):
        sid = _id()
        await self._w(
            """INSERT INTO client_segments(id,event_id,client_id,exposure_type,
               exposure_amount,exposure_pct,risk_level,segment_label) VALUES(?,?,?,?,?,?,?,?)""",
            (sid, d["event_id"], d["client_id"], d.get("exposure_type"),
             d.get("exposure_amount",0), d.get("exposure_pct",0),
             d.get("risk_level","medium"), d.get("segment_label")))
        return {"id": sid, **d}

    async def get_segments_for_event(self, event_id):
        return await self._q(
            """SELECT cs.*, c.name, c.email, c.channel_preference
               FROM client_segments cs JOIN clients c ON cs.client_id=c.id
               WHERE cs.event_id=? ORDER BY cs.exposure_amount DESC""", (event_id,))

    # ── Communications ──
    async def queue_message(self, d):
        mid = _id()
        await self._w(
            """INSERT INTO communications(id,client_id,event_id,workflow_id,channel,
               message_type,subject,content,status) VALUES(?,?,?,?,?,?,?,?,?)""",
            (mid, d["client_id"], d.get("event_id"), d.get("workflow_id"),
             d.get("channel","email"), d.get("message_type","advisory"),
             d.get("subject"), d["content"], "queued"))
        return {"id": mid, "status": "queued"}

    async def update_comm_status(self, mid, status, gmail_id=None):
        if gmail_id:
            await self._w("UPDATE communications SET status=?,gmail_message_id=?,sent_at=datetime('now') WHERE id=?",
                          (status, gmail_id, mid))
        else:
            await self._w("UPDATE communications SET status=?,sent_at=datetime('now') WHERE id=?", (status, mid))

    async def list_communications(self, workflow_id=None, status=None, limit=50):
        sql, p = "SELECT * FROM communications WHERE 1=1", []
        if workflow_id: sql += " AND workflow_id=?"; p.append(workflow_id)
        if status: sql += " AND status=?"; p.append(status)
        sql += " ORDER BY created_at DESC LIMIT ?"; p.append(limit)
        return await self._q(sql, tuple(p))

    # ── Scheduled Events ──
    async def create_scheduled_event(self, d):
        sid = _id()
        await self._w(
            """INSERT INTO scheduled_events(id,client_id,workflow_id,title,description,
               start_time,end_time,attendees,calendar_event_id,status) VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (sid, d.get("client_id"), d.get("workflow_id"), d["title"],
             d.get("description"), d["start_time"], d.get("end_time"),
             json.dumps(d.get("attendees",[])), d.get("calendar_event_id"), "scheduled"))
        return {"id": sid, "status": "scheduled"}

    async def list_scheduled_events(self, workflow_id=None, limit=50):
        sql, p = "SELECT * FROM scheduled_events WHERE 1=1", []
        if workflow_id: sql += " AND workflow_id=?"; p.append(workflow_id)
        sql += " ORDER BY start_time ASC LIMIT ?"; p.append(limit)
        return await self._q(sql, tuple(p))

    # ── Interactions ──
    async def log_interaction(self, d):
        iid = _id()
        await self._w(
            """INSERT INTO interactions(id,client_id,interaction_type,channel,
               subject,summary,direction,logged_by) VALUES(?,?,?,?,?,?,?,?)""",
            (iid, d["client_id"], d["interaction_type"], d.get("channel"),
             d.get("subject"), d.get("summary"), d.get("direction","outbound"),
             d.get("logged_by","system")))
        return {"id": iid}

    async def get_client_interactions(self, client_id, limit=10):
        return await self._q(
            "SELECT * FROM interactions WHERE client_id=? ORDER BY interaction_date DESC LIMIT ?",
            (client_id, limit))

    # ── Workflow Logs ──
    async def log_step(self, wf_id, step, agent, action, **kw):
        lid = _id()
        await self._w(
            """INSERT INTO workflow_logs(id,workflow_id,step_number,agent,action,
               input_summary,output_summary,status,duration_ms,error_message) VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (lid, wf_id, step, agent, action, kw.get("input_summary"),
             kw.get("output_summary"), kw.get("status","running"),
             kw.get("duration_ms"), kw.get("error_message")))
        return {"id": lid}

    async def get_workflow_log(self, wf_id):
        return await self._q("SELECT * FROM workflow_logs WHERE workflow_id=? ORDER BY step_number", (wf_id,))

    # ── Cleanup ──
    async def close(self):
        if self._pg_pool:
            await self._pg_pool.close()


async def get_db():
    global _inst
    if _inst is None:
        _inst = DatabaseManager()
        await _inst.init()
    return _inst