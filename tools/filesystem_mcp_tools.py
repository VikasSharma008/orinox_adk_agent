"""
ORINOX v3 Filesystem MCP Tools
Uses the official MCP Filesystem server to save generated content.
Briefs, advisory reports, portfolio exports, delivery logs.
"""
import os
import json
from datetime import datetime
from tools.registry import get_registry
from tools.mcp_servers import get_mcp_process

FS_ROOT = os.getenv("MCP_FS_ROOT", "/tmp/orinox_output")


async def _call_fs_mcp(tool_name: str, arguments: dict) -> dict | None:
    """Call Filesystem MCP server via stdio JSON-RPC."""
    proc = get_mcp_process("filesystem")
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
            return resp.get("result", {})
    except Exception as e:
        print(f"Filesystem MCP error: {e}")
    return None


def _ensure_dir(subdir: str = ""):
    path = os.path.join(FS_ROOT, subdir) if subdir else FS_ROOT
    os.makedirs(path, exist_ok=True)
    return path


async def fs_write_file(filename: str, content: str, subdir: str = "") -> dict:
    """
    Write content to a file via MCP Filesystem server.
    Falls back to direct file write if MCP unavailable.
    """
    _ensure_dir(subdir)
    filepath = os.path.join(FS_ROOT, subdir, filename) if subdir else os.path.join(FS_ROOT, filename)

    # Try MCP
    mcp_result = await _call_fs_mcp("write_file", {"path": filepath, "content": content})
    if mcp_result is not None:
        return {"file": filepath, "size": len(content), "via": "filesystem_mcp"}

    # Fallback: direct write
    try:
        with open(filepath, "w") as f:
            f.write(content)
        return {"file": filepath, "size": len(content), "via": "direct_fallback"}
    except Exception as e:
        return {"error": str(e), "file": filepath}


async def fs_read_file(filepath: str) -> dict:
    """Read a file via MCP Filesystem server."""
    mcp_result = await _call_fs_mcp("read_file", {"path": filepath})
    if mcp_result is not None:
        content = ""
        for c in mcp_result.get("content", []):
            if c.get("type") == "text":
                content += c.get("text", "")
        return {"file": filepath, "content": content, "via": "filesystem_mcp"}

    try:
        with open(filepath, "r") as f:
            content = f.read()
        return {"file": filepath, "content": content, "via": "direct_fallback"}
    except Exception as e:
        return {"error": str(e), "file": filepath}


async def fs_list_directory(dirpath: str = None) -> dict:
    """List files in a directory via MCP Filesystem server."""
    target = dirpath or FS_ROOT
    mcp_result = await _call_fs_mcp("list_directory", {"path": target})
    if mcp_result is not None:
        return {"directory": target, "entries": mcp_result, "via": "filesystem_mcp"}

    try:
        entries = os.listdir(target)
        return {"directory": target, "entries": entries, "via": "direct_fallback"}
    except Exception as e:
        return {"error": str(e)}


async def fs_save_brief(client_name: str, brief_content: str,
                         workflow_id: str = None) -> dict:
    """Save a pre-call brief as a markdown file."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = client_name.replace(" ", "_").lower()
    filename = f"brief_{safe_name}_{ts}.md"

    header = f"# Pre-Call Brief: {client_name}\n"
    header += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
    if workflow_id:
        header += f"Workflow: {workflow_id}\n"
    header += "---\n\n"

    return await fs_write_file(filename, header + brief_content, subdir="briefs")


async def fs_save_advisory_report(event_title: str, clients_count: int,
                                    messages_summary: list,
                                    workflow_id: str = None) -> dict:
    """Save an advisory campaign report after market event response."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = event_title[:30].replace(" ", "_").lower()
    filename = f"advisory_{safe_title}_{ts}.md"

    content = f"# Advisory Report: {event_title}\n"
    content += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
    content += f"Workflow: {workflow_id or 'N/A'}\n"
    content += f"Clients impacted: {clients_count}\n"
    content += "---\n\n"
    content += "## Messages Sent\n\n"

    for i, msg in enumerate(messages_summary[:20], 1):
        content += f"{i}. **{msg.get('client_name', 'Unknown')}** — "
        content += f"{msg.get('status', 'queued')} via {msg.get('channel', 'email')}\n"

    return await fs_write_file(filename, content, subdir="advisories")


async def fs_save_schedule_export(events: list, workflow_id: str = None) -> dict:
    """Export scheduled events as a markdown file."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"schedule_export_{ts}.md"

    content = f"# Schedule Export\n"
    content += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
    content += f"Workflow: {workflow_id or 'N/A'}\n"
    content += f"Total events: {len(events)}\n"
    content += "---\n\n"

    for evt in events:
        content += f"- **{evt.get('title', 'Event')}** — {evt.get('start_time', 'TBD')}"
        if evt.get('client_name'):
            content += f" ({evt['client_name']})"
        content += "\n"

    return await fs_write_file(filename, content, subdir="schedules")


def register_filesystem_mcp_tools():
    r = get_registry()

    r.register("fs_write_file",
        "Write content to a file via MCP Filesystem server",
        {"type": "object", "properties": {
            "filename": {"type": "string"}, "content": {"type": "string"},
            "subdir": {"type": "string"}
        }, "required": ["filename", "content"]},
        fs_write_file, "all")

    r.register("fs_read_file",
        "Read a file via MCP Filesystem server",
        {"type": "object", "properties": {
            "filepath": {"type": "string"}
        }, "required": ["filepath"]},
        fs_read_file, "all")

    r.register("fs_list_directory",
        "List files in a directory via MCP Filesystem server",
        {"type": "object", "properties": {
            "dirpath": {"type": "string"}
        }},
        fs_list_directory, "all")

    r.register("fs_save_brief",
        "Save a pre-call brief as a markdown file via MCP Filesystem",
        {"type": "object", "properties": {
            "client_name": {"type": "string"}, "brief_content": {"type": "string"},
            "workflow_id": {"type": "string"}
        }, "required": ["client_name", "brief_content"]},
        fs_save_brief, "client")

    r.register("fs_save_advisory_report",
        "Save an advisory campaign report via MCP Filesystem after market event response",
        {"type": "object", "properties": {
            "event_title": {"type": "string"}, "clients_count": {"type": "integer"},
            "messages_summary": {"type": "array"}, "workflow_id": {"type": "string"}
        }, "required": ["event_title", "clients_count", "messages_summary"]},
        fs_save_advisory_report, "comms")

    r.register("fs_save_schedule_export",
        "Export scheduled events as a file via MCP Filesystem",
        {"type": "object", "properties": {
            "events": {"type": "array"}, "workflow_id": {"type": "string"}
        }, "required": ["events"]},
        fs_save_schedule_export, "schedule")
