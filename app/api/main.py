"""FastAPI API endpoints for the multi-agent system."""

from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models import Base, WorkflowModel, AuditLogModel, ApprovalRequestModel
from app.schemas import (
    WorkflowCreate,
    WorkflowResponse,
    TraceEntry,
    TraceResponse,
)
from app.observability import setup_logging
from app.graph.orchestrator import WorkflowOrchestrator


app = FastAPI(
    title="Multi-Agent AI Workflow API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.workflow_orchestrator = None
app.state.session_factory = None

setup_logging(settings.LOG_LEVEL)


@app.on_event("startup")
async def startup_event():
    """Initialize database and workflow orchestrator."""

    engine = create_engine(settings.DATABASE_URL)

    Base.metadata.create_all(bind=engine)

    app.state.session_factory = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
    )

    app.state.workflow_orchestrator = WorkflowOrchestrator()


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown application resources."""
    pass


def workflow_to_response(workflow: WorkflowModel) -> WorkflowResponse:
    """Convert a database workflow model to an API response."""

    return WorkflowResponse(
        id=workflow.id,
        name="unnamed_workflow",
        description=None,
        request=workflow.request,
        status=workflow.status,
        plan=workflow.plan,
        current_step=workflow.current_step,
        current_agent=workflow.current_agent,
        created_at=workflow.created_at,
        updated_at=workflow.updated_at,
        completed_at=workflow.completed_at,
        approval_status=workflow.approval_status,
        metadata=workflow.workflow_metadata or {},
    )


@app.post(
    "/workflows",
    response_model=WorkflowResponse,
    status_code=201,
)
async def create_workflow(workflow: WorkflowCreate):
    """Create and execute a workflow."""

    workflow_id = str(__import__("uuid").uuid4())

    session = app.state.session_factory()

    try:
        db_workflow = WorkflowModel(
            id=workflow_id,
            request=workflow.request,
            status="running",
            current_step=0,
            current_agent="planner",
            plan=None,
            approval_status=None,
            workflow_metadata={},
        )

        session.add(db_workflow)

        session.add(
            AuditLogModel(
                id=str(__import__("uuid").uuid4()),
                workflow_id=workflow_id,
                event_type="workflow_created",
                message="Workflow created",
                data={"request": workflow.request},
                agent="planner",
            )
        )

        session.commit()

        orchestrator = app.state.workflow_orchestrator

        execution = await orchestrator.execute_workflow(
            workflow_id=workflow_id,
            initial_request=workflow.request,
        )

        if not execution.get("success"):
            db_workflow.status = "failed"
            session.commit()

            raise HTTPException(
                status_code=500,
                detail=execution.get(
                    "error",
                    "Workflow execution failed",
                ),
            )

        result = execution.get("result", {})

        # Persist final workflow state.
        db_workflow.status = result.get("status", "completed")
        db_workflow.plan = result.get("plan")
        db_workflow.current_step = result.get("current_step", 0)
        db_workflow.current_agent = result.get("current_agent")

        workflow_results = result.get("results", {})
        synthesis_result = workflow_results.get("synthesis", {})
        execution_trace = result.get("execution_trace", [])

        for trace in execution_trace:
            session.add(
                AuditLogModel(
                    id=str(__import__("uuid").uuid4()),
                    workflow_id=workflow_id,
                    event_type=trace.get(
                        "event_type",
                        "agent_completed",
                    ),
                    message=trace.get(
                        "message",
                        "Agent execution completed",
                    ),
                    data=trace.get("data", {}),
                    agent=trace.get("agent"),
                    tool=trace.get("tool"),
                )
            )

        db_workflow.completed_at = (
            datetime.now(timezone.utc)
            if db_workflow.status == "completed"
            else None
        )

        db_workflow.updated_at = datetime.now(timezone.utc)

        session.add(
            AuditLogModel(
                id=str(__import__("uuid").uuid4()),
                workflow_id=workflow_id,
                event_type="workflow_completed",
                message="Workflow execution completed",
                data={
                    "status": db_workflow.status,
                    "current_step": db_workflow.current_step,
                    "current_agent": db_workflow.current_agent,
                    "synthesized_response": synthesis_result.get(
                        "synthesized_response",
                        ""
                    ),
                },
                agent=db_workflow.current_agent,
            )
        )

        session.commit()
        session.refresh(db_workflow)

        return workflow_to_response(db_workflow)

    finally:
        session.close()


@app.get(
    "/workflows/{workflow_id}",
    response_model=WorkflowResponse,
)
async def get_workflow(workflow_id: str):
    """Get the actual workflow state from PostgreSQL."""

    session = app.state.session_factory()

    try:
        workflow = session.get(WorkflowModel, workflow_id)

        if workflow is None:
            raise HTTPException(
                status_code=404,
                detail=f"Workflow {workflow_id} not found",
            )

        return workflow_to_response(workflow)

    finally:
        session.close()


@app.get(
    "/workflows/{workflow_id}/trace",
    response_model=TraceResponse,
)
async def get_workflow_trace(workflow_id: str):
    """Get the actual execution trace from audit logs."""

    session = app.state.session_factory()

    try:
        workflow = session.get(WorkflowModel, workflow_id)

        if workflow is None:
            raise HTTPException(
                status_code=404,
                detail=f"Workflow {workflow_id} not found",
            )

        logs = (
            session.query(AuditLogModel)
            .filter(AuditLogModel.workflow_id == workflow_id)
            .order_by(AuditLogModel.created_at.asc())
            .all()
        )

        entries = [
            TraceEntry(
                timestamp=log.created_at,
                event_type=log.event_type,
                agent=log.agent,
                tool=log.tool,
                message=log.message,
                data=log.data,
            )
            for log in logs
        ]

        return TraceResponse(
            workflow_id=workflow_id,
            entries=entries,
        )

    finally:
        session.close()


@app.post(
    "/workflows/{workflow_id}/approve",
    response_model=WorkflowResponse,
)
async def approve_workflow(workflow_id: str):
    """Approve a pending workflow."""

    session = app.state.session_factory()

    try:
        workflow = session.get(WorkflowModel, workflow_id)

        if workflow is None:
            raise HTTPException(
                status_code=404,
                detail=f"Workflow {workflow_id} not found",
            )

        workflow.approval_status = "approved"

        if workflow.status == "paused_approval":
            workflow.status = "resuming"

        workflow.updated_at = datetime.now(timezone.utc)

        session.add(
            AuditLogModel(
                id=str(__import__("uuid").uuid4()),
                workflow_id=workflow_id,
                event_type="workflow_approved",
                message="Workflow approved",
                data={"approval_status": "approved"},
                agent=workflow.current_agent,
            )
        )

        session.commit()
        session.refresh(workflow)

        return workflow_to_response(workflow)

    finally:
        session.close()


@app.post(
    "/workflows/{workflow_id}/reject",
    response_model=WorkflowResponse,
)
async def reject_workflow(workflow_id: str):
    """Reject a workflow."""

    session = app.state.session_factory()

    try:
        workflow = session.get(WorkflowModel, workflow_id)

        if workflow is None:
            raise HTTPException(
                status_code=404,
                detail=f"Workflow {workflow_id} not found",
            )

        workflow.approval_status = "rejected"
        workflow.status = "rejected"
        workflow.completed_at = datetime.now(timezone.utc)
        workflow.updated_at = datetime.now(timezone.utc)

        session.add(
            AuditLogModel(
                id=str(__import__("uuid").uuid4()),
                workflow_id=workflow_id,
                event_type="workflow_rejected",
                message="Workflow rejected",
                data={"approval_status": "rejected"},
                agent=workflow.current_agent,
            )
        )

        session.commit()
        session.refresh(workflow)

        return workflow_to_response(workflow)

    finally:
        session.close()


@app.get("/health")
async def health_check():
    """Health check endpoint."""

    return JSONResponse(
        content={
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.api.main:app",
        host="0.0.0.0",
        port=settings.APP_PORT,
        reload=True,
    )