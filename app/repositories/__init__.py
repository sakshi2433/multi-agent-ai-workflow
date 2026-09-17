"""Repository pattern for database operations."""
from typing import Any, Dict, List, Optional

from sqlalchemy import select, update, delete
from sqlalchemy.orm import Session

from app.models import WorkflowModel, ToolCallLogModel, AuditLogModel


class BaseRepository:
    """Base repository class for database operations."""

    def __init__(self, session: Session, model: type):
        self.session = session
        self.model = model

    def create(self, data: Dict[str, Any]) -> Any:
        """Create a new record."""
        obj = self.model(**data)
        self.session.add(obj)
        self.session.commit()
        self.session.refresh(obj)
        return obj

    def get_by_id(self, id: str) -> Optional[Any]:
        """Get a record by ID."""
        return self.session.get(self.model, id)

    def update(self, id: str, data: Dict[str, Any]) -> bool:
        """Update a record."""
        stmt = update(self.model).where(self.model.id == id).values(**data)
        result = self.session.execute(stmt)
        self.session.commit()
        return result.rowcount > 0

    def delete(self, id: str) -> bool:
        """Delete a record."""
        stmt = delete(self.model).where(self.model.id == id)
        result = self.session.execute(stmt)
        self.session.commit()
        return result.rowcount > 0


class WorkflowRepository(BaseRepository):
    """Repository for workflow operations."""

    def __init__(self, session: Session):
        super().__init__(session, WorkflowModel)

    def get_all(self, limit: int = 100, offset: int = 0) -> List[WorkflowModel]:
        """Get all workflows with pagination."""
        stmt = select(self.model).limit(limit).offset(offset)
        return list(self.session.execute(stmt).scalars().all())

    def get_by_status(self, status: str) -> List[WorkflowModel]:
        """Get workflows by status."""
        stmt = select(self.model).where(self.model.status == status)
        return list(self.session.execute(stmt).scalars().all())


class ToolCallRepository(BaseRepository):
    """Repository for tool call operations."""

    def __init__(self, session: Session):
        super().__init__(session, ToolCallLogModel)

    def get_by_workflow(self, workflow_id: str) -> List[ToolCallLogModel]:
        """Get tool calls by workflow ID."""
        stmt = select(self.model).where(self.model.workflow_id == workflow_id)
        return list(self.session.execute(stmt).scalars().all())


class AuditRepository(BaseRepository):
    """Repository for audit log operations."""

    def __init__(self, session: Session):
        super().__init__(session, AuditLogModel)

    def get_by_workflow(self, workflow_id: str) -> List[AuditLogModel]:
        """Get audit logs by workflow ID."""
        stmt = select(self.model).where(self.model.workflow_id == workflow_id)
        return list(self.session.execute(stmt).scalars().all())