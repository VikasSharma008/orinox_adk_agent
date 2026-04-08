"""ORINOX v3 API Schemas"""
from pydantic import BaseModel, Field
from typing import Optional

class ChatRequest(BaseModel):
    message: str = Field(..., description="Natural language message from RM")

class ChatResponse(BaseModel):
    workflow_id: str
    intent: str
    summary: str
    results: list
    plan: dict
    total_duration_ms: int

class WorkflowRequest(BaseModel):
    intent: str
    params: dict = Field(default_factory=dict)

class HealthResponse(BaseModel):
    status: str = "healthy"
    version: str = "3.0.0"
    agents: list[str] = []
    tools_count: int = 0
    mcp_servers: dict = {}
