"""Shared Pydantic schemas for the multi-agent system."""
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class WorkflowStatus(str, Enum):
    PENDING = "pending"
    PLANNING = "planning"
    RUNNING = "running"
    PAUSED_APPROVAL = "paused_approval"
    RESUMING = "resuming"
    COMPLETED = "completed"
    FAILED = "failed"
    LIMITED = "limited"
    REJECTED = "rejected"


class AgentType(str, Enum):
    PLANNER = "planner"
    RESEARCH = "research"
    DATABASE = "database"
    CODE = "code"
    SYNTHESIS = "synthesis"


class ToolStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"


class WorkflowBase(BaseModel):
    id: str | None = None
    name: str = Field(default="unnamed_workflow")
    description: str | None = None


class WorkflowCreate(WorkflowBase):
    request: str


class WorkflowResponse(WorkflowBase):
    id: str
    request: str
    status: WorkflowStatus
    plan: dict[str, Any] | None = None
    current_step: int | None = None
    current_agent: str | None = None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None
    approval_status: str | None = None
    metadata: dict[str, Any] | None = None


class WorkflowState(BaseModel):
    id: str
    request: str
    status: WorkflowStatus
    current_step: int
    current_agent: str | None = None
    plan: dict[str, Any] | None = None
    results: dict[str, Any] | None = None
    execution_trace: list[dict[str, Any]] = Field(default_factory=list)


class StepStatus(str, Enum):
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class ToolCallBase(BaseModel):
    tool_name: str
    input_data: dict[str, Any]
    timeout_seconds: int = 30


class ToolCallResponse(ToolCallBase):
    output_data: Any
    status: ToolStatus
    error: str | None = None
    execution_time_ms: float | None = None
    retry_count: int = 0


class TraceEntry(BaseModel):
    timestamp: datetime
    event_type: str
    agent: str | None = None
    tool: str | None = None
    message: str
    data: dict[str, Any] | None = None


class TraceResponse(BaseModel):
    workflow_id: str
    entries: list[TraceEntry]