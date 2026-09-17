"""Observability module for the multi-agent system."""
import json
import logging
from typing import Any, Dict, List

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models import WorkflowModel, ToolCallLogModel, AuditLogModel


class DatabaseObservability:
    """Database-based observability."""

    def __init__(self, database_url: str):
        self.engine = create_engine(database_url)
        SessionLocal = sessionmaker(bind=self.engine)
        self.session = SessionLocal()

    def get_workflow_trace(self, workflow_id: str) -> Dict[str, Any]:
        """Get execution trace for a workflow."""
        # Get workflow details
        workflow = self.session.query(WorkflowModel).filter(WorkflowModel.id == workflow_id).first()
        
        # Get tool calls
        tool_calls = self.session.query(ToolCallLogModel).filter(ToolCallLogModel.workflow_id == workflow_id).order_by(ToolCallLogModel.created_at).all()
        
        # Get audit logs
        audit_logs = self.session.query(AuditLogModel).filter(AuditLogModel.workflow_id == workflow_id).order_by(AuditLogModel.created_at).all()
        
        # Build trace
        trace = {
            "workflow_id": workflow_id,
            "request": workflow.request,
            "status": workflow.status,
            "created_at": workflow.created_at.isoformat(),
            "updated_at": workflow.updated_at.isoformat(),
            "completed_at": workflow.completed_at.isoformat() if workflow.completed_at else None,
            "plan": workflow.plan,
            "trace": []
        }
        
        # Convert tool calls to trace entries
        for call in tool_calls:
            trace["trace"].append({
                "timestamp": call.created_at.isoformat(),
                "event_type": "tool_call",
                "tool": call.tool_name,
                "message": f"Tool call: {call.tool_name}",
                "data": {
                    "input": call.input_data,
                    "output": call.output_data,
                    "error": call.error,
                    "status": call.status,
                    "execution_time_ms": call.execution_time_ms,
                    "retry_count": call.retry_count
                }
            })
        
        # Convert audit logs to trace entries
        for log in audit_logs:
            trace["trace"].append({
                "timestamp": log.created_at.isoformat(),
                "event_type": log.event_type,
                "agent": log.agent,
                "tool": log.tool,
                "message": log.message,
                "data": log.data
            })
        
        return trace

    def export_traces(self, output_path: str = "traces.json") -> None:
        """Export all traces to a file."""
        workflows = self.session.query(WorkflowModel).all()
        
        traces = []
        for workflow in workflows:
            traces.append(self.get_workflow_trace(workflow.id))
        
        with open(output_path, "w") as f:
            json.dump(traces, f, indent=2, default=str)


def setup_logging(level: str = "INFO") -> logging.Logger:
    """Set up logging configuration."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    return logging.getLogger(__name__)