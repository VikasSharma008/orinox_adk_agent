"""
ORINOX v3 Memory MCP Tools
Uses the official MCP Memory server for persistent client relationship context.
The knowledge graph survives across requests — remembers client preferences,
past advisory themes, relationship notes.
"""
import json
from tools.registry import get_registry
from tools.mcp_servers import get_mcp_process


async def _call_memory_mcp(tool_name: str, arguments: dict) -> dict | None:
    """Call Memory MCP server via stdio JSON-RPC."""
    proc = get_mcp_process("memory")
    if not proc or proc.poll() is not None:
        return None
    try:
        request = json.dumps({
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments}
        }) + "\n"
        proc.stdin.write(request.encode())
        proc.stdin.flush()
        line = proc.stdout.readline().decode().strip()
        if line:
            resp = json.loads(line)
            content = resp.get("result", {}).get("content", [])
            text = "\n".join(c.get("text", "") for c in content if c.get("type") == "text")
            return {"result": text, "via": "memory_mcp"}
    except Exception as e:
        print(f"Memory MCP error: {e}")
    return None


# In-memory fallback when MCP server is unavailable
_local_memory: dict[str, dict] = {}


async def memory_store_entity(entity_name: str, entity_type: str,
                               observations: list[str]) -> dict:
    """
    Store an entity in the knowledge graph.
    Used to remember: client preferences, past advisory context, relationship notes.
    """
    mcp_result = await _call_memory_mcp("create_entities", {
        "entities": [{"name": entity_name, "entityType": entity_type,
                      "observations": observations}]
    })
    if mcp_result:
        return {"stored": entity_name, "type": entity_type, "via": "memory_mcp"}

    # Fallback
    _local_memory[entity_name] = {
        "type": entity_type, "observations": observations
    }
    return {"stored": entity_name, "type": entity_type, "via": "local_fallback"}


async def memory_add_observation(entity_name: str, observation: str) -> dict:
    """Add an observation to an existing entity in the knowledge graph."""
    mcp_result = await _call_memory_mcp("add_observations", {
        "observations": [{"entityName": entity_name, "contents": [observation]}]
    })
    if mcp_result:
        return {"entity": entity_name, "added": observation, "via": "memory_mcp"}

    if entity_name in _local_memory:
        _local_memory[entity_name]["observations"].append(observation)
    else:
        _local_memory[entity_name] = {"type": "unknown", "observations": [observation]}
    return {"entity": entity_name, "added": observation, "via": "local_fallback"}


async def memory_create_relation(from_entity: str, to_entity: str,
                                  relation_type: str) -> dict:
    """Create a relationship between two entities in the knowledge graph."""
    mcp_result = await _call_memory_mcp("create_relations", {
        "relations": [{"from": from_entity, "to": to_entity, "relationType": relation_type}]
    })
    if mcp_result:
        return {"from": from_entity, "to": to_entity, "relation": relation_type, "via": "memory_mcp"}

    return {"from": from_entity, "to": to_entity, "relation": relation_type, "via": "local_fallback"}


async def memory_search(query: str) -> dict:
    """Search the knowledge graph for entities matching a query."""
    mcp_result = await _call_memory_mcp("search_nodes", {"query": query})
    if mcp_result:
        return {"query": query, "results": mcp_result.get("result", ""), "via": "memory_mcp"}

    # Local fallback — simple keyword search
    matches = []
    query_lower = query.lower()
    for name, data in _local_memory.items():
        if query_lower in name.lower() or any(query_lower in o.lower() for o in data.get("observations", [])):
            matches.append({"name": name, **data})
    return {"query": query, "results": matches, "via": "local_fallback"}


async def memory_get_entity(entity_name: str) -> dict:
    """Get all information about a specific entity."""
    mcp_result = await _call_memory_mcp("open_nodes", {"names": [entity_name]})
    if mcp_result:
        return {"entity": entity_name, "data": mcp_result.get("result", ""), "via": "memory_mcp"}

    data = _local_memory.get(entity_name)
    if data:
        return {"entity": entity_name, "data": data, "via": "local_fallback"}
    return {"entity": entity_name, "data": None, "error": "Not found"}


async def memory_store_client_context(client_name: str, context: dict) -> dict:
    """
    Convenience: store a rich client context entity.
    Called after pre-call briefs and advisory generation to build up the knowledge graph.
    """
    observations = []
    if context.get("risk_profile"):
        observations.append(f"Risk profile: {context['risk_profile']}")
    if context.get("last_advisory"):
        observations.append(f"Last advisory: {context['last_advisory']}")
    if context.get("key_holdings"):
        observations.append(f"Key holdings: {', '.join(context['key_holdings'][:5])}")
    if context.get("preferences"):
        observations.append(f"Preferences: {context['preferences']}")
    if context.get("notes"):
        observations.append(context["notes"])

    return await memory_store_entity(
        entity_name=client_name,
        entity_type="client",
        observations=observations
    )


def register_memory_mcp_tools():
    r = get_registry()

    r.register("memory_store_entity",
        "Store an entity (client, event, concept) in the persistent knowledge graph via MCP Memory server",
        {"type": "object", "properties": {
            "entity_name": {"type": "string"}, "entity_type": {"type": "string"},
            "observations": {"type": "array", "items": {"type": "string"}}
        }, "required": ["entity_name", "entity_type", "observations"]},
        memory_store_entity, "client")

    r.register("memory_add_observation",
        "Add a new observation to an existing entity in the knowledge graph",
        {"type": "object", "properties": {
            "entity_name": {"type": "string"}, "observation": {"type": "string"}
        }, "required": ["entity_name", "observation"]},
        memory_add_observation, "client")

    r.register("memory_create_relation",
        "Create a relationship between two entities (e.g. client → holds → instrument)",
        {"type": "object", "properties": {
            "from_entity": {"type": "string"}, "to_entity": {"type": "string"},
            "relation_type": {"type": "string"}
        }, "required": ["from_entity", "to_entity", "relation_type"]},
        memory_create_relation, "client")

    r.register("memory_search",
        "Search the knowledge graph for entities matching a query",
        {"type": "object", "properties": {
            "query": {"type": "string"}
        }, "required": ["query"]},
        memory_search, "all")

    r.register("memory_store_client_context",
        "Store rich client context (risk profile, last advisory, holdings, notes) in knowledge graph",
        {"type": "object", "properties": {
            "client_name": {"type": "string"}, "context": {"type": "object"}
        }, "required": ["client_name", "context"]},
        memory_store_client_context, "client")
