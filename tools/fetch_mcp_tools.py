"""
ORINOX v3 Fetch MCP Tools
Uses the official MCP Fetch server to pull live web content.
Falls back to httpx if MCP server is unavailable.
"""
import json
import httpx
from tools.registry import get_registry
from tools.mcp_servers import get_mcp_process


async def _call_fetch_mcp(url: str) -> dict | None:
    """Call Fetch MCP server via stdio JSON-RPC."""
    proc = get_mcp_process("fetch")
    if not proc or proc.poll() is not None:
        return None
    try:
        request = json.dumps({
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": "fetch", "arguments": {"url": url}}
        }) + "\n"
        proc.stdin.write(request.encode())
        proc.stdin.flush()
        line = proc.stdout.readline().decode().strip()
        if line:
            resp = json.loads(line)
            content = resp.get("result", {}).get("content", [])
            text = "\n".join(c.get("text", "") for c in content if c.get("type") == "text")
            return {"content": text, "url": url, "via": "fetch_mcp"}
    except Exception as e:
        print(f"Fetch MCP error: {e}")
    return None


async def fetch_url(url: str, max_length: int = 5000) -> dict:
    """
    Fetch a URL and return its content as text.
    Tries MCP Fetch server first, falls back to httpx.
    """
    # Try MCP server
    mcp_result = await _call_fetch_mcp(url)
    if mcp_result and mcp_result.get("content"):
        content = mcp_result["content"][:max_length]
        return {"url": url, "content": content, "length": len(content), "via": "fetch_mcp"}

    # Fallback: direct httpx
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            content = resp.text[:max_length]
            return {"url": url, "content": content, "length": len(content), "via": "httpx_fallback"}
    except Exception as e:
        return {"url": url, "error": str(e), "via": "failed"}


async def fetch_market_news(query: str) -> dict:
    """
    Fetch market news from multiple financial sources.
    Uses Fetch MCP to pull live content from pre-defined financial URLs.
    """
    # Financial news sources (free, no auth)
    sources = [
        f"https://www.google.com/finance/quote/{query}",
        f"https://economictimes.indiatimes.com/topic/{query.replace(' ', '-')}",
    ]

    results = []
    for url in sources:
        result = await fetch_url(url, max_length=3000)
        if "error" not in result:
            results.append({"source": url, "snippet": result["content"][:500], "via": result["via"]})

    return {
        "query": query,
        "sources_fetched": len(results),
        "results": results,
    }


async def fetch_rbi_announcement(url: str = None) -> dict:
    """Fetch latest RBI policy announcement page."""
    target = url or "https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx"
    return await fetch_url(target, max_length=5000)


def register_fetch_mcp_tools():
    r = get_registry()
    r.register("fetch_url",
        "Fetch any URL and return its content as text via MCP Fetch server",
        {"type": "object", "properties": {
            "url": {"type": "string", "description": "URL to fetch"},
            "max_length": {"type": "integer", "description": "Max content length"}
        }, "required": ["url"]},
        fetch_url, "market")

    r.register("fetch_market_news",
        "Fetch live market news from financial websites via MCP Fetch server",
        {"type": "object", "properties": {
            "query": {"type": "string", "description": "Market topic to search for"}
        }, "required": ["query"]},
        fetch_market_news, "market")

    r.register("fetch_rbi_announcement",
        "Fetch latest RBI policy announcement via MCP Fetch server",
        {"type": "object", "properties": {
            "url": {"type": "string", "description": "Optional specific RBI URL"}
        }},
        fetch_rbi_announcement, "market")
