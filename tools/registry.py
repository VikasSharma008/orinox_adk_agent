"""ORINOX v2 Tool Registry"""
from typing import Callable, Any

class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, dict] = {}

    def register(self, name, description, parameters, handler, scope="all"):
        self._tools[name] = {"name":name,"description":description,"parameters":parameters,"handler":handler,"scope":scope}

    async def call(self, name, **kw):
        if name not in self._tools:
            return {"error": f"Tool '{name}' not found"}
        try:
            return await self._tools[name]["handler"](**kw)
        except Exception as e:
            return {"error": f"{name} failed: {e}"}

    def for_agent(self, scope):
        return [{"name":t["name"],"description":t["description"],"parameters":t["parameters"]}
                for t in self._tools.values() if t["scope"] in (scope,"all")]

    def all_schemas(self):
        return [{"name":t["name"],"description":t["description"],"parameters":t["parameters"],"scope":t["scope"]}
                for t in self._tools.values()]

    @property
    def names(self): return list(self._tools.keys())

_reg = None
def get_registry():
    global _reg
    if _reg is None: _reg = ToolRegistry()
    return _reg
