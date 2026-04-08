"""
ORINOX v3 MCP Server Manager
Manages lifecycle of MCP server subprocesses (Fetch, Memory, Filesystem).
All three are official Anthropic MCP servers — zero config, run via npx.
"""
import os
import asyncio
import subprocess
import signal
import atexit
from typing import Optional

# MCP server config
MCP_SERVERS = {
    #"fetch": {
    #    "command": ["npx", "-y", "@modelcontextprotocol/server-fetch"],
    #    "description": "Fetch web content and convert to markdown for LLM consumption",
    #},
    "memory": {
        "command": ["npx", "-y", "@modelcontextprotocol/server-memory"],
        "description": "Knowledge graph-based persistent memory system",
    },
    "filesystem": {
        "command": ["npx", "-y", "@modelcontextprotocol/server-filesystem",
                    os.getenv("MCP_FS_ROOT", "/tmp/orinox_output")],
        "description": "Secure file operations — read, write, search files",
    },
}

_processes: dict[str, subprocess.Popen] = {}


def start_mcp_servers():
    """Start all MCP servers as background subprocesses (stdio transport)."""
    fs_root = os.getenv("MCP_FS_ROOT", "/tmp/orinox_output")
    os.makedirs(fs_root, exist_ok=True)

    for name, config in MCP_SERVERS.items():
        if os.getenv(f"MCP_{name.upper()}_ENABLED", "true").lower() != "true":
            print(f"  MCP {name}: disabled")
            continue
        try:
            proc = subprocess.Popen(
                config["command"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            _processes[name] = proc
            print(f"  MCP {name}: started (pid={proc.pid})")
        except FileNotFoundError:
            print(f"  MCP {name}: npx not found — server disabled (install Node.js)")
        except Exception as e:
            print(f"  MCP {name}: failed to start — {e}")


def stop_mcp_servers():
    """Stop all running MCP server subprocesses."""
    for name, proc in _processes.items():
        try:
            proc.terminate()
            proc.wait(timeout=5)
            print(f"  MCP {name}: stopped")
        except Exception:
            proc.kill()
            print(f"  MCP {name}: killed")
    _processes.clear()


def get_mcp_process(name: str) -> Optional[subprocess.Popen]:
    """Get a running MCP server process by name."""
    return _processes.get(name)


def get_mcp_status() -> dict:
    """Get status of all MCP servers."""
    status = {}
    for name in MCP_SERVERS:
        proc = _processes.get(name)
        if proc and proc.poll() is None:
            status[name] = "running"
        elif proc:
            status[name] = f"exited ({proc.returncode})"
        else:
            status[name] = "disabled"
    return status


# Cleanup on exit
atexit.register(stop_mcp_servers)
