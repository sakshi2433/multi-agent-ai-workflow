"""SQLAlchemy ORM models for the multi-agent system."""
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import (
    Column,
    String,
    DateTime,
    Float,
    Integer,
    ForeignKey,
    JSON,
    Text,
    func,
)
from sqlalchemy.orm import declarative_base, relationship

# Create the declarative base
Base = declarative_base()


class WorkflowModel(Base):
    """Database model for workflow instances."""
    __tablename__ = "workflows"

    id = Column(String(36), primary_key=True, nullable=False)
    request = Column(Text, nullable=False)
    status = Column(String(50), nullable=False, default="pending")
    plan = Column(JSON, nullable=True, default=None)
    current_step = Column(Integer, nullable=True, default=0)
    current_agent = Column(String(50), nullable=True)
    approval_status = Column(String(50), nullable=True)
    workflow_metadata = Column(JSON, nullable=True, default=None)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    tool_calls = relationship("ToolCallLogModel", back_populates="workflow", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLogModel", back_populates="workflow", cascade="all, delete-orphan")
    approval_requests = relationship("ApprovalRequestModel", back_populates="workflow", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<WorkflowModel(id={self.id}, status={self.status})>"


class ToolCallLogModel(Base):
    """Database model for tool call execution logs."""
    __tablename__ = "tool_call_logs"

    id = Column(String(36), primary_key=True, nullable=False)
    workflow_id = Column(String(36), ForeignKey("workflows.id"), nullable=False)
    tool_name = Column(String(255), nullable=False)
    input_data = Column(JSON, nullable=True)
    output_data = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="pending")
    execution_time_ms = Column(Float, nullable=True, default=0.0)
    retry_count = Column(Integer, nullable=False, default=0)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    workflow = relationship("WorkflowModel", back_populates="tool_calls")

    def __repr__(self):
        return f"<ToolCallLogModel(id={self.id}, tool_name={self.tool_name}, status={self.status})>"


class AuditLogModel(Base):
    """Database model for audit logs."""
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, nullable=False)
    workflow_id = Column(String(36), ForeignKey("workflows.id"), nullable=False)
    event_type = Column(String(100), nullable=False)
    message = Column(Text, nullable=False)
    data = Column(JSON, nullable=True)
    agent = Column(String(100), nullable=True)
    tool = Column(String(100), nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    workflow = relationship("WorkflowModel", back_populates="audit_logs")

    def __repr__(self):
        return f"<AuditLogModel(id={self.id}, event_type={self.event_type})>"


class ApprovalRequestModel(Base):
    """Database model for approval requests."""
    __tablename__ = "approval_requests"

    id = Column(String(36), primary_key=True, nullable=False)
    workflow_id = Column(String(36), ForeignKey("workflows.id"), nullable=False)
    status = Column(String(50), nullable=False, default="pending")
    request_data = Column(JSON, nullable=True)
    response_data = Column(JSON, nullable=True)
    approved_by = Column(String(255), nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)

    # Relationships
    workflow = relationship("WorkflowModel", back_populates="approval_requests")

    def __repr__(self):
        return f"<ApprovalRequestModel(id={self.id}, status={self.status})>"
