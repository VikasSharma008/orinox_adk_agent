"""ORINOX v3 Market Tools — yfinance + Gemini search grounding"""
import json
from config import generate_content
from tools.registry import get_registry
from db.database import get_db


async def market_search(query: str) -> dict:
    prompt = f"""You are a financial market analyst. Analyze: {query}
Respond in JSON: {{"summary":"...","affected_sectors":["..."],"affected_instrument_types":["..."],"severity":"low|medium|high|critical","recommendations":["..."],"key_data_points":["..."]}}"""
    try:
        t = generate_content(prompt).strip()
        if "```json" in t: t = t.split("```json")[1].split("```")[0].strip()
        elif "```" in t: t = t.split("```")[1].split("```")[0].strip()
        return json.loads(t)
    except Exception as e:
        return {"error": str(e)}

async def market_get_stock_data(symbol: str, period: str = "1mo") -> dict:
    try:
        import yfinance as yf
        tk = yf.Ticker(symbol)
        info = tk.info
        hist = tk.history(period=period)
        return {"symbol":symbol,"name":info.get("longName",symbol),"sector":info.get("sector","Unknown"),
                "current_price":info.get("currentPrice",info.get("regularMarketPrice")),
                "previous_close":info.get("previousClose"),"market_cap":info.get("marketCap"),
                "52w_high":info.get("fiftyTwoWeekHigh"),"52w_low":info.get("fiftyTwoWeekLow"),
                "recent_closes":[round(p,2) for p in hist["Close"].tail(5).tolist()] if not hist.empty else []}
    except Exception as e:
        return {"error": str(e)}

async def market_analyze_impact(event_description: str, sectors: list = None) -> dict:
    ctx = f"Focus on: {', '.join(sectors)}" if sectors else ""
    prompt = f"""Senior market strategist analysis. Event: {event_description} {ctx}
JSON: {{"event_title":"...","event_type":"rate_change|policy|earnings|geopolitical|sector_specific",
"impact_analysis":"2-3 sentences","sector_impacts":[{{"sector":"...","direction":"positive|negative|neutral","magnitude":"low|medium|high","explanation":"..."}}],
"instrument_impacts":[{{"type":"bonds|equities|real_estate|mutual_funds|reits","direction":"...","magnitude":"..."}}],
"risk_level":"low|medium|high|critical","action_urgency":"monitor|advise|urgent_action"}}"""
    try:
        t = generate_content(prompt).strip()
        if "```json" in t: t = t.split("```json")[1].split("```")[0].strip()
        elif "```" in t: t = t.split("```")[1].split("```")[0].strip()
        result = json.loads(t)
        db = await get_db()
        ev = await db.create_market_event({
            "title":result.get("event_title",event_description[:100]),"description":event_description,
            "event_type":result.get("event_type"),"severity":result.get("risk_level","medium"),
            "affected_sectors":[s["sector"] for s in result.get("sector_impacts",[])],
            "affected_instruments":[i["type"] for i in result.get("instrument_impacts",[])],
            "impact_analysis":result.get("impact_analysis"),"source":"gemini_analysis"})
        result["event_id"] = ev["id"]
        return result
    except Exception as e:
        return {"error": str(e)}

def register_market_tools():
    r = get_registry()
    r.register("market_search","Search market news and analysis",
        {"type":"object","properties":{"query":{"type":"string"}},"required":["query"]},
        market_search, "market")
    r.register("market_get_stock_data","Get stock price and sector data",
        {"type":"object","properties":{"symbol":{"type":"string"},"period":{"type":"string"}},"required":["symbol"]},
        market_get_stock_data, "market")
    r.register("market_analyze_impact","Analyze market event impact on sectors and instruments",
        {"type":"object","properties":{"event_description":{"type":"string"},"sectors":{"type":"array","items":{"type":"string"}}},
         "required":["event_description"]}, market_analyze_impact, "market")
