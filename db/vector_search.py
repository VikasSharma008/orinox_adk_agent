"""ORINOX v3 Vector Search — Gemini embeddings + in-memory cosine similarity (dev) / pgvector (prod)"""
import math
from config import embed_text as _embed

_vectors: dict[str, list[float]] = {}

async def embed_text(text: str) -> list[float]:
    try:
        return _embed(text)
    except Exception as e:
        print(f"Embedding error: {e}")
        return []

def cosine_sim(a, b):
    if not a or not b or len(a) != len(b): return 0.0
    dot = sum(x*y for x,y in zip(a,b))
    na = math.sqrt(sum(x*x for x in a))
    nb = math.sqrt(sum(x*x for x in b))
    return dot/(na*nb) if na and nb else 0.0

class VectorSearch:
    async def store(self, key, text):
        v = await embed_text(text)
        if v: _vectors[key] = v

    async def search(self, query, top_k=10):
        qv = await embed_text(query)
        if not qv: return []
        scores = [{"key":k, "similarity":round(cosine_sim(qv,v),4)} for k,v in _vectors.items()]
        scores.sort(key=lambda x: x["similarity"], reverse=True)
        return scores[:top_k]

    async def build_index(self, db):
        clients = await db.list_clients(limit=1000)
        n = 0
        for c in clients:
            port = await db.get_portfolio(c["id"])
            if port:
                desc = self._describe(c, port)
                await self.store(f"client:{c['id']}", desc)
                n += 1
        return n

    def _describe(self, client, holdings):
        parts = [f"Client: {client['name']}, Risk: {client.get('risk_profile','moderate')}, AUM: {client.get('aum',0)}"]
        by_type = {}
        for h in holdings:
            by_type.setdefault(h.get("instrument_type","other"), []).append(h)
        for t, items in by_type.items():
            names = [i["instrument_name"] for i in items[:5]]
            total = sum(i.get("current_value",0) for i in items)
            secs = set(i.get("sector","") for i in items if i.get("sector"))
            parts.append(f"{t}: {', '.join(names)} (value: {total}, sectors: {', '.join(secs)})")
        return ". ".join(parts)

    async def find_exposed(self, event_desc, db, threshold=0.3, top_k=100):
        results = await self.search(event_desc, top_k)
        exposed = []
        for r in results:
            if r["similarity"] >= threshold:
                cid = r["key"].replace("client:","")
                c = await db.get_client(cid)
                if c: exposed.append({**c, "similarity_score": r["similarity"]})
        return exposed
