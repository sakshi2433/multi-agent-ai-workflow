"""Core graph workflow for the multi-agent system."""

import logging
from typing import Any, Dict

from langgraph.graph import StateGraph

from app.agents.base import PlannerAgent, SynthesisAgent
from app.agents.research import ResearchAgent
from app.agents.database import DatabaseAgent
from app.agents.code import CodeAgent
from app.schemas import WorkflowState
from app.core.config import settings
from app.clients.llm import LLMClient


# Optional: Import PostgresCheckpoint if available
try:
    from langgraph.checkpoint.postgres import PostgresCheckpoint
except ImportError:
    PostgresCheckpoint = None


class WorkflowOrchestrator:
    """Orchestrator for the multi-agent workflow."""

    def __init__(self):
        self.graph = StateGraph(WorkflowState)

        self.checkpointer = None

        if PostgresCheckpoint is not None:
            self.checkpointer = PostgresCheckpoint(
                settings.DATABASE_URL
            )

        self.logger = logging.getLogger(__name__)

        # Initialize LLM client
        llm_client = LLMClient(
            timeout=settings.LLM_TIMEOUT_SECONDS,
            offline_mode=(settings.LLM_MODE == "offline"),
        )

        # Initialize agents
        self.planner = PlannerAgent(
            llm_client=llm_client
        )

        self.synthesis_agent = SynthesisAgent(
            llm_client=llm_client
        )

        self.research_agent = ResearchAgent()
        self.database_agent = DatabaseAgent()
        self.code_agent = CodeAgent()

        self.setup_workflow()

    def _add_trace(
        self,
        state: WorkflowState,
        event_type: str,
        agent: str,
        message: str,
        tool: str | None = None,
        data: dict[str, Any] | None = None,
    ) -> None:
        """Add an execution trace entry to workflow state."""

        if state.execution_trace is None:
            state.execution_trace = []

        state.execution_trace.append(
            {
                "event_type": event_type,
                "agent": agent,
                "tool": tool,
                "message": message,
                "data": data or {},
            }
        )

    def setup_workflow(self) -> None:
        """Set up the workflow graph."""

        # Define workflow nodes
        self.graph.add_node(
            "planner",
            self._planner_node
        )

        self.graph.add_node(
            "research_worker",
            self._research_worker_node
        )

        self.graph.add_node(
            "database_worker",
            self._database_worker_node
        )

        self.graph.add_node(
            "code_worker",
            self._code_worker_node
        )

        self.graph.add_node(
            "synthesis",
            self._synthesis_node
        )

        # Planner -> conditional routing to workers or synthesis
        self.graph.add_conditional_edges(
            "planner",
            self._route_to_worker,
            {
                "research_worker": "research_worker",
                "database_worker": "database_worker",
                "code_worker": "code_worker",
                "synthesis": "synthesis",
            },
        )

        # Research worker -> next worker or synthesis
        self.graph.add_conditional_edges(
            "research_worker",
            self._route_to_worker,
            {
                "research_worker": "research_worker",
                "database_worker": "database_worker",
                "code_worker": "code_worker",
                "synthesis": "synthesis",
            },
        )

        # Database worker -> next worker or synthesis
        self.graph.add_conditional_edges(
            "database_worker",
            self._route_to_worker,
            {
                "research_worker": "research_worker",
                "database_worker": "database_worker",
                "code_worker": "code_worker",
                "synthesis": "synthesis",
            },
        )

        # Code worker -> next worker or synthesis
        self.graph.add_conditional_edges(
            "code_worker",
            self._route_to_worker,
            {
                "research_worker": "research_worker",
                "database_worker": "database_worker",
                "code_worker": "code_worker",
                "synthesis": "synthesis",
            },
        )

        # Synthesis ends the workflow
        self.graph.add_edge(
            "synthesis",
            "__end__"
        )

        # Set entry point
        self.graph.set_entry_point("planner")

    def _route_to_worker(
        self,
        state: WorkflowState,
    ) -> str:
        """Route to appropriate worker or synthesis."""

        if not state.plan or "subtasks" not in state.plan:
            return "synthesis"

        subtasks = state.plan.get(
            "subtasks",
            []
        )

        if not subtasks:
            return "synthesis"

        current_step = state.current_step or 0

        if current_step >= len(subtasks):
            return "synthesis"

        subtask = subtasks[current_step]

        agent_type = subtask.get(
            "agent",
            "research"
        )

        return f"{agent_type}_worker"

    async def _planner_node(
        self,
        state: WorkflowState,
    ) -> Dict[str, Any]:
        """Planner node - breaks down the task into subtasks."""

        self.logger.info(
            f"[PLANNER] Processing request: {state.request}"
        )

        state.status = "planning"
        state.current_agent = "planner"

        task = {
            "request": state.request,
            "max_steps": settings.MAX_WORKFLOW_STEPS,
        }

        try:
            result = await self.planner.process(task)

            if result.get("success", False):
                state.plan = result.get(
                    "plan",
                    {}
                )

                state.current_step = 0

                subtasks = state.plan.get(
                    "subtasks",
                    []
                )

                self.logger.info(
                    f"[PLANNER] Plan created with "
                    f"{len(subtasks)} subtasks"
                )

                self._add_trace(
                    state=state,
                    event_type="agent_completed",
                    agent="planner",
                    message=(
                        f"Planner created "
                        f"{len(subtasks)} subtasks"
                    ),
                    data={
                        "step": 0,
                        "subtask_count": len(subtasks),
                        "subtasks": subtasks,
                    },
                )

            else:
                state.status = "failed"

                error = result.get(
                    "error",
                    "Unknown planning error"
                )

                self.logger.error(
                    f"[PLANNER] Failed to create plan: {error}"
                )

                self._add_trace(
                    state=state,
                    event_type="agent_failed",
                    agent="planner",
                    message="Planner failed to create a plan",
                    data={
                        "step": 0,
                        "error": error,
                    },
                )

        except Exception as e:
            state.status = "failed"

            self.logger.error(
                f"[PLANNER] Error: {e}"
            )

            self._add_trace(
                state=state,
                event_type="agent_failed",
                agent="planner",
                message="Planner execution failed",
                data={
                    "step": 0,
                    "error": str(e),
                },
            )

        return {
            "status": state.status,
            "plan": state.plan,
            "current_step": 0,
            "current_agent": "planner",
            "execution_trace": state.execution_trace,
        }

    async def _research_worker_node(
        self,
        state: WorkflowState,
    ) -> Dict[str, Any]:
        """Research worker node - executes research tasks."""

        current_step = state.current_step or 0

        if not state.plan or "subtasks" not in state.plan:
            self.logger.warning(
                "[RESEARCH] No plan found"
            )

            return {
                "results": state.results or {},
                "execution_trace": state.execution_trace,
            }

        subtasks = state.plan.get(
            "subtasks",
            []
        )

        if current_step >= len(subtasks):
            self.logger.warning(
                f"[RESEARCH] No more subtasks "
                f"(step {current_step} >= {len(subtasks)})"
            )

            return {
                "results": state.results or {},
                "current_step": current_step,
                "execution_trace": state.execution_trace,
            }

        subtask = subtasks[current_step]

        task_query = subtask.get(
            "task",
            ""
        )

        self.logger.info(
            f"[RESEARCH] Executing research for: "
            f"{task_query}"
        )

        try:
            result = await self.research_agent.research(
                task_query
            )

            if state.results is None:
                state.results = {}

            state.results[
                f"research_{current_step}"
            ] = result

            self._add_trace(
                state=state,
                event_type="agent_completed",
                agent="research",
                tool="web_search",
                message=(
                    f"Research completed: "
                    f"{task_query}"
                ),
                data={
                    "step": current_step,
                    "query": task_query,
                    "results_found": result.get(
                        "total_results",
                        0,
                    ),
                    "success": result.get(
                        "success",
                        False,
                    ),
                    "sources": [
                        {
                            "title": item.get(
                                "title"
                            ),
                            "url": item.get(
                                "url"
                            ),
                        }
                        for item in result.get(
                            "findings",
                            [],
                        )
                    ],
                },
            )

            self.logger.info(
                f"[RESEARCH] Completed: "
                f"{result.get('success')}"
            )

            state.current_step = current_step + 1
            state.current_agent = "research"

            return {
                "results": state.results,
                "current_step": state.current_step,
                "current_agent": "research",
                "execution_trace": state.execution_trace,
            }

        except Exception as e:
            self.logger.error(
                f"[RESEARCH] Error: {e}"
            )

            if state.results is None:
                state.results = {}

            state.results[
                f"research_{current_step}"
            ] = {
                "success": False,
                "error": str(e),
                "findings": [],
            }

            self._add_trace(
                state=state,
                event_type="agent_failed",
                agent="research",
                tool="web_search",
                message="Research execution failed",
                data={
                    "step": current_step,
                    "query": task_query,
                    "error": str(e),
                },
            )

            state.current_step = current_step + 1
            state.current_agent = "research"

            return {
                "results": state.results,
                "current_step": state.current_step,
                "current_agent": "research",
                "execution_trace": state.execution_trace,
            }

    async def _database_worker_node(
        self,
        state: WorkflowState,
    ) -> Dict[str, Any]:
        """Database worker node - executes database queries."""

        current_step = state.current_step or 0

        if not state.plan or "subtasks" not in state.plan:
            self.logger.warning(
                "[DATABASE] No plan found"
            )

            return {
                "results": state.results or {},
                "execution_trace": state.execution_trace,
            }

        subtasks = state.plan.get(
            "subtasks",
            []
        )

        if current_step >= len(subtasks):
            self.logger.warning(
                f"[DATABASE] No more subtasks "
                f"(step {current_step} >= {len(subtasks)})"
            )

            return {
                "results": state.results or {},
                "current_step": current_step,
                "execution_trace": state.execution_trace,
            }

        subtask = subtasks[current_step]

        task_query = subtask.get(
            "task",
            ""
        )

        self.logger.info(
            f"[DATABASE] Executing query for: "
            f"{task_query}"
        )

        try:
            result = await self.database_agent.query(
                task_query
            )

            if state.results is None:
                state.results = {}

            state.results[
                f"database_{current_step}"
            ] = result

            self._add_trace(
                state=state,
                event_type="agent_completed",
                agent="database",
                tool="database_query",
                message="Database query completed",
                data={
                    "step": current_step,
                    "query": task_query,
                    "row_count": result.get(
                        "row_count",
                        0,
                    ),
                    "success": result.get(
                        "success",
                        False,
                    ),
                },
            )

            self.logger.info(
                f"[DATABASE] Completed: "
                f"{result.get('success')}"
            )

            state.current_step = current_step + 1
            state.current_agent = "database"

            return {
                "results": state.results,
                "current_step": state.current_step,
                "current_agent": "database",
                "execution_trace": state.execution_trace,
            }

        except Exception as e:
            self.logger.error(
                f"[DATABASE] Error: {e}"
            )

            if state.results is None:
                state.results = {}

            state.results[
                f"database_{current_step}"
            ] = {
                "success": False,
                "error": str(e),
                "rows": [],
            }

            self._add_trace(
                state=state,
                event_type="agent_failed",
                agent="database",
                tool="database_query",
                message="Database execution failed",
                data={
                    "step": current_step,
                    "query": task_query,
                    "error": str(e),
                },
            )

            state.current_step = current_step + 1
            state.current_agent = "database"

            return {
                "results": state.results,
                "current_step": state.current_step,
                "current_agent": "database",
                "execution_trace": state.execution_trace,
            }

    async def _code_worker_node(
        self,
        state: WorkflowState,
    ) -> Dict[str, Any]:
        """Code worker node - analyzes and executes code."""

        current_step = state.current_step or 0

        if not state.plan or "subtasks" not in state.plan:
            self.logger.warning(
                "[CODE] No plan found"
            )

            return {
                "results": state.results or {},
                "execution_trace": state.execution_trace,
            }

        subtasks = state.plan.get(
            "subtasks",
            []
        )

        if current_step >= len(subtasks):
            self.logger.warning(
                f"[CODE] No more subtasks "
                f"(step {current_step} >= {len(subtasks)})"
            )

            return {
                "results": state.results or {},
                "current_step": current_step,
                "execution_trace": state.execution_trace,
            }

        subtask = subtasks[current_step]

        task_code = subtask.get(
            "task",
            ""
        )

        self.logger.info(
            f"[CODE] Analyzing code for: "
            f"{task_code[:50]}"
        )

        try:
            result = await self.code_agent.analyze_code(
                task_code,
                subtask.get(
                    "description",
                    "",
                ),
            )

            if state.results is None:
                state.results = {}

            state.results[
                f"code_{current_step}"
            ] = result

            self._add_trace(
                state=state,
                event_type="agent_completed",
                agent="code",
                tool="code_analysis",
                message="Code analysis completed",
                data={
                    "step": current_step,
                    "task": task_code,
                    "success": result.get(
                        "success",
                        False,
                    ),
                    "analysis": result.get(
                        "analysis",
                        {},
                    ),
                },
            )

            self.logger.info(
                f"[CODE] Completed: "
                f"{result.get('success')}"
            )

            state.current_step = current_step + 1
            state.current_agent = "code"

            return {
                "results": state.results,
                "current_step": state.current_step,
                "current_agent": "code",
                "execution_trace": state.execution_trace,
            }

        except Exception as e:
            self.logger.error(
                f"[CODE] Error: {e}"
            )

            if state.results is None:
                state.results = {}

            state.results[
                f"code_{current_step}"
            ] = {
                "success": False,
                "error": str(e),
                "analysis": {},
            }

            self._add_trace(
                state=state,
                event_type="agent_failed",
                agent="code",
                tool="code_analysis",
                message="Code analysis failed",
                data={
                    "step": current_step,
                    "task": task_code,
                    "error": str(e),
                },
            )

            state.current_step = current_step + 1
            state.current_agent = "code"

            return {
                "results": state.results,
                "current_step": state.current_step,
                "current_agent": "code",
                "execution_trace": state.execution_trace,
            }

    async def _synthesis_node(
        self,
        state: WorkflowState,
    ) -> Dict[str, Any]:
        """Synthesis node - combines results into final response."""

        self.logger.info(
            "[SYNTHESIS] Starting synthesis of results"
        )

        state.current_agent = "synthesis"

        all_results = state.results or {}

        try:
            synthesis_task = {
                "workflow_id": state.id,
                "request": state.request,
                "results": all_results,
            }

            synthesis_result = await self.synthesis_agent.process(
                synthesis_task
            )

            if state.results is None:
                state.results = {}

            state.results[
                "synthesis"
            ] = synthesis_result

            self._add_trace(
                state=state,
                event_type="agent_completed",
                agent="synthesis",
                message="Synthesis completed",
                data={
                    "step": state.current_step,
                    "worker_results": len(all_results),
                    "success": synthesis_result.get(
                        "success",
                        False,
                    ),
                },
            )

            state.status = "completed"

            self.logger.info(
                "[SYNTHESIS] Synthesis completed successfully"
            )

            return {
                "status": "completed",
                "results": state.results,
                "current_agent": "synthesis",
                "execution_trace": state.execution_trace,
            }

        except Exception as e:
            self.logger.error(
                f"[SYNTHESIS] Error: {e}"
            )

            self._add_trace(
                state=state,
                event_type="agent_failed",
                agent="synthesis",
                message="Synthesis failed",
                data={
                    "step": state.current_step,
                    "error": str(e),
                },
            )

            state.status = "failed"

            return {
                "status": "failed",
                "results": state.results or {},
                "current_agent": "synthesis",
                "execution_trace": state.execution_trace,
            }

    def compile(self):
        """Compile the workflow graph."""

        return self.graph.compile(
            checkpointer=self.checkpointer
        )

    async def execute_workflow(
        self,
        workflow_id: str,
        initial_request: str,
    ) -> Dict[str, Any]:
        """Execute a workflow."""

        self.logger.info(
            f"[EXECUTE] Starting workflow "
            f"{workflow_id}: {initial_request}"
        )

        initial_state = WorkflowState(
            id=workflow_id,
            request=initial_request,
            status="pending",
            current_step=0,
            results={},
            execution_trace=[],
        )

        compiled_graph = self.compile()

        try:
            result = await compiled_graph.ainvoke(
                initial_state
            )

            self.logger.info(
                f"[EXECUTE] Workflow "
                f"{workflow_id} completed"
            )

            return {
                "workflow_id": workflow_id,
                "result": result,
                "success": True,
            }

        except Exception as e:
            self.logger.error(
                f"[EXECUTE] Workflow "
                f"{workflow_id} failed: {e}"
            )

            return {
                "workflow_id": workflow_id,
                "error": str(e),
                "success": False,
            }