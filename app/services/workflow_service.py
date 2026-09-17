"""Workflow service for business logic."""
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models import WorkflowModel, ToolCallLogModel, AuditLogModel
from app.repositories import WorkflowRepository, ToolCallRepository, AuditRepository
from app.core.config import settings


class WorkflowService:
    """Service for workflow business logic."""

    def __init__(self, db_session: Session):
        self.db = db_session
        self.workflow_repo = WorkflowRepository(db_session)
        self.tool_call_repo = ToolCallRepository(db_session)
        self.audit_repo = AuditRepository(db_session)
        self.logger = logging.getLogger(__name__)

    async def create_workflow(self, request: str) -> WorkflowModel:
        """Create a new workflow."""
        workflow_id = str(__import__("uuid").uuid4())
        workflow = self.workflow_repo.create({
            "id": workflow_id,
            "request": request,
            "status": "pending"
        })
        
        # Log audit event
        self.audit_repo.create({
            "workflow_id": workflow_id,
            "event_type": "workflow_created",
            "message": f"Workflow created for request: {request}",
            "data": {"request": request}
        })
        
        return workflow

    async def get_workflow(self, workflow_id: str) -> Optional[WorkflowModel]:
        """Get workflow by ID."""
        return self.workflow_repo.get_by_id(workflow_id)

    async def update_workflow_status(self, workflow_id: str, status: str) -> bool:
        """Update workflow status."""
        workflow = await self.get_workflow(workflow_id)
        if not workflow:
            return False
            
        return self.workflow_repo.update(workflow_id, {"status": status})

    async def save_tool_call(self, workflow_id: str, tool_name: str, input_data: Dict[str, Any],
                           output_data: Any = None, error: str = None,
                           status: str = "success", execution_time_ms: float = 0.0,
                           retry_count: int = 0) -> ToolCallLogModel:
        """Save tool call to database."""
        tool_call = self.tool_call_repo.create({
            "workflow_id": workflow_id,
            "tool_name": tool_name,
            "input_data": input_data,
            "output_data": output_data,
            "error": error,
            "status": status,
            "execution_time_ms": execution_time_ms,
            "retry_count": retry_count
        })
        
        return tool_call

    async def save_audit_log(self, workflow_id: str, event_type: str, message: str,
                           data: Dict[str, Any] = None, agent: str = None,
                           tool: str = None) -> AuditLogModel:
        """Save audit log."""
        audit_log = self.audit_repo.create({
            "workflow_id": workflow_id,
            "event_type": event_type,
            "message": message,
            "data": data,
            "agent": agent,
            "tool": tool
        })
        
        return audit_log