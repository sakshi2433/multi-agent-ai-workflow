"""Base agent implementation."""
import asyncio
import json
import logging
from typing import Any, Dict, Optional

from app.tools.base import BaseTool, ToolResponse
from app.clients.llm import LLMClient


class BaseAgent:
    """Base class for all agents."""

    name: str = "base_agent"
    description: str = "Base agent"

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.tools: Dict[str, BaseTool] = {}

    def register_tool(self, tool: BaseTool) -> None:
        """Register a tool with the agent."""
        self.tools[tool.name] = tool
        self.logger.debug(f"Tool registered: {tool.name}")

    async def execute_tool(self, tool_name: str, input_data: Dict[str, Any]) -> ToolResponse:
        """Execute a registered tool."""
        if tool_name not in self.tools:
            return ToolResponse(
                tool_name=tool_name,
                status="failed",
                output_data=None,
                error=f"Tool not found: {tool_name}"
            )

        tool = self.tools[tool_name]
        return await tool.execute(input_data)

    async def process(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process a task - to be implemented by subclasses."""
        raise NotImplementedError("Subclass must implement process method")


class PlannerAgent(BaseAgent):
    """Agent that plans and decomposes tasks."""

    name = "planner_agent"
    description = "Decomposes high-level tasks into executable plans"

    def __init__(self, llm_client: Optional[LLMClient] = None):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.llm_client = llm_client

    async def process(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Create a plan from a high-level task."""
        self.logger.info(f"Planner agent processing task: {task}")

        request = task.get("request", "")
        max_steps = task.get("max_steps", 10)

        # Decompose request into subtasks using LLM if available
        subtasks = await self._decompose_request(request)

        # Create plan
        plan = {
            "request": request,
            "subtasks": subtasks,
            "max_steps": max_steps,
            "step_count": 0
        }

        return {
            "success": True,
            "plan": plan,
            "error": None
        }

    async def _decompose_request(self, request: str) -> list[Dict[str, Any]]:
        """Decompose request into subtasks using LLM or fallback."""
        if not request:
            return []

        # Try to use LLM if available
        if self.llm_client:
            subtasks = await self._decompose_with_llm(request)
            if subtasks is not None:
                return subtasks
            self.logger.warning("LLM decomposition failed, falling back to keyword matching")

        # Fallback to keyword matching
        return self._decompose_with_keywords(request)

    async def _decompose_with_llm(self, request: str) -> Optional[list[Dict[str, Any]]]:
        """Decompose request using LLM.
        
        Args:
            request: User request string
            
        Returns:
            List of subtasks or None if decomposition failed
        """
        prompt = f"""You are the planning agent in a multi-agent AI workflow.

            Break the user's request into a set of specific, executable subtasks.

            Your goal is to make sure EVERY important requirement in the user's request is covered.

            Rules:
            1. Identify every entity, technology, product, or topic that must be investigated.
            2. Identify every comparison criterion or question that must be answered.
            3. Use the research agent for factual information that requires web research.
            4. Use the database agent only when the request requires database access or SQL execution.
            5. Use the code agent only when the request requires code analysis, generation, or execution.
            6. Do not create unnecessary subtasks.
            7. For comparison/research requests, create focused research subtasks that collectively cover ALL requested dimensions.
            8. Each subtask must be independently understandable.
            9. Prefer 3-8 focused subtasks for complex requests.

            Available agent types:
            - research: web research, factual information, comparisons, documentation, current information
            - database: SQL queries and database data retrieval
            - code: code analysis, programming, code generation

            User request:
            {request}

            Return ONLY valid JSON using this exact structure:

            {{
                "subtasks": [
                    {{
                        "agent": "research",
                        "task": "specific research task",
                        "description": "what this subtask should investigate"
                    }}
                ]
            }}

            Do not omit important requirements from the user's request.
            Do not answer the user's question yourself.
            """

        result = await self.llm_client.parse_json(
            prompt=prompt,
            expected_keys=["subtasks"],
            temperature=0.3,
        )

        if not result["success"]:
            self.logger.error(f"LLM decomposition error: {result['error']}")
            return None

        try:
            subtasks = result["data"].get("subtasks", [])
            if not subtasks:
                self.logger.warning("LLM returned empty subtasks list")
                return None

            # Validate subtask structure
            for subtask in subtasks:
                if not all(k in subtask for k in ["agent", "task", "description"]):
                    self.logger.error(f"Invalid subtask structure: {subtask}")
                    return None
                if subtask["agent"] not in ["research", "database", "code"]:
                    self.logger.error(f"Invalid agent type: {subtask['agent']}")
                    return None

            self.logger.info(f"LLM created {len(subtasks)} subtasks")
            return subtasks

        except Exception as e:
            self.logger.error(f"Error processing LLM response: {str(e)}")
            return None

    def _decompose_with_keywords(self, request: str) -> list[Dict[str, Any]]:
        """Decompose request using keyword matching.
        
        This is a fallback when LLM is not available or fails.
        """
        subtasks = []

        # Determine agent type based on request keywords
        if any(word in request.lower() for word in ["search", "find", "research", "web", "look up"]):
            subtasks.append({
                "agent": "research",
                "task": request,
                "description": "Research the requested topic"
            })
        elif any(word in request.lower() for word in ["query", "database", "sql", "retrieve"]):
            subtasks.append({
                "agent": "database",
                "task": request,
                "description": "Query the database"
            })
        elif any(word in request.lower() for word in ["code", "analyze", "fix", "generate", "write"]):
            subtasks.append({
                "agent": "code",
                "task": request,
                "description": "Analyze or generate code"
            })
        else:
            # Default to research for unknown tasks
            subtasks.append({
                "agent": "research",
                "task": request,
                "description": "Research the requested topic"
            })

        self.logger.info(f"Keyword matching created {len(subtasks)} subtasks")
        return subtasks

class SynthesisAgent(BaseAgent):
    """Agent that synthesizes results from worker agents."""

    name = "synthesis_agent"
    description = "Combines results from worker agents into a coherent response"

    def __init__(self, llm_client: Optional[LLMClient] = None):
        super().__init__()
        self.llm_client = llm_client

    async def process(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Synthesize results from worker agents."""

        self.logger.info("Synthesis agent processing results")

        results = task.get("results", {})
        workflow_id = task.get("workflow_id", "")
        original_request = task.get("request", "")

        successful_results = []
        failed_results = []

        for key, result in results.items():
            if key == "synthesis":
                continue

            if isinstance(result, dict) and result.get("success", False):
                successful_results.append({
                    "key": key,
                    "data": result,
                })
            else:
                failed_results.append({
                    "key": key,
                    "data": result,
                })

        combined_result = {
            "workflow_id": workflow_id,
            "total_results": len(successful_results),
            "successful_results": successful_results,
            "failed_results": failed_results,
            "synthesized_response": "",
            "success": False,
        }

        if not successful_results:
            combined_result["synthesized_response"] = (
                "No successful worker results were available to answer the request."
            )
            return combined_result

        # Generate the actual final answer.
        synthesized = await self._generate_response(
            combined_result,
            original_request,
        )

        if synthesized:
            combined_result["synthesized_response"] = synthesized
            combined_result["success"] = True
        else:
            combined_result["synthesized_response"] = (
                "The workflow completed, but the synthesis agent "
                "could not generate a final response."
            )

        return combined_result

    async def _generate_response(
        self,
        combined_result: Dict[str, Any],
        original_request: str,
    ) -> Optional[str]:
        """Generate the final user-facing response."""

        if self.llm_client:
            response = await self._generate_with_llm(
                combined_result,
                original_request,
            )

            if response:
                return response

            self.logger.warning(
                "LLM synthesis failed."
            )

        return self._generate_simple_response(
            combined_result,
            original_request,
        )

    async def _generate_with_llm(
        self,
        combined_result: Dict[str, Any],
        original_request: str,
    )   -> Optional[str]:
        """Generate a concise final answer from worker results."""

        if not self.llm_client:
            return None

        worker_results = []

        for item in combined_result["successful_results"]:
            data = item["data"]

            if "findings" in data:
                findings = data.get("findings", [])

                compact_findings = []

                for finding in findings[:5]:
                    if not isinstance(finding, dict):
                        continue

                    title = str(finding.get("title", ""))[:200]
                    snippet = str(
                        finding.get("snippet", "")
                    )[:700]
                    url = str(finding.get("url", ""))[:300]

                    compact_findings.append({
                        "title": title,
                        "finding": snippet,
                        "source": url,
                    })

                worker_results.append({
                    "agent": "research",
                    "query": data.get("query", ""),
                    "findings": compact_findings,
                })

            elif "rows" in data:
                worker_results.append({
                    "agent": "database",
                    "rows": data.get("rows", [])[:20],
                })

            elif "analysis" in data:
                worker_results.append({
                    "agent": "code",
                    "analysis": str(data.get("analysis", ""))[:1500],
                })

            else:
                worker_results.append({
                    "agent": item["key"],
                    "data": str(data)[:1500],
                })

        results_summary = json.dumps(
            worker_results,
            indent=2,
            ensure_ascii=False,
        )

        prompt = f"""
    You are the final synthesis agent in a multi-agent AI workflow.

    ORIGINAL USER REQUEST:
    {original_request}

    RESEARCH AND WORKER EVIDENCE:
    {results_summary}

    Your job is to produce the final answer to the ORIGINAL USER REQUEST.

    IMPORTANT RULES:

    1. Answer the user's request directly.
    2. Do not describe the multi-agent workflow.
    3. Do not mention that you are a synthesis agent.
    4. Do not output raw JSON.
    5. Do not simply repeat research snippets.
    6. Combine the evidence into one coherent technical answer.
    7. Cover every requirement in the original request.
    8. For comparisons, compare all requested options.
    9. Use clear Markdown headings.
    10. Use a Markdown comparison table when appropriate.
    11. Explain important trade-offs.
    12. Give practical use cases.
    13. Distinguish benchmark-specific findings from general characteristics.
    14. Do not treat one benchmark as universally representative.
    15. Do not invent facts that are not supported by the evidence.
    16. If sources disagree, acknowledge the disagreement briefly.
    17. Prefer primary/official sources when the evidence provides them.
    18. Keep the answer concise but technically useful.
    19. Include a short "Sources" section with the most relevant URLs.
    20. Return ONLY the final answer.

    Write the final response now.
    """

        try:
            self.logger.info(
                f"[SYNTHESIS] Sending compact prompt: "
                f"{len(prompt)} characters"
            )

            result = await self.llm_client.generate(
                prompt=prompt,
                temperature=0.2,
                max_tokens=2000,
            )

            if not result.get("success"):
                self.logger.error(
                    f"LLM synthesis error: "
                    f"{result.get('error', 'Unknown error')}"
                )
                return None

            content = result.get("content", "")

            if not content or not content.strip():
                self.logger.error(
                    "LLM returned empty synthesis response."
                )
                return None

            self.logger.info(
                f"[SYNTHESIS] Generated "
                f"{len(content)} characters"
            )

            return content.strip()

        except Exception as e:
            self.logger.exception(
                f"[SYNTHESIS] Exception: {e}"
            )
            return None
        
    def _generate_simple_response(
        self,
        combined_result: Dict[str, Any],
        original_request: str,
    ) -> str:
        """Fallback response if LLM synthesis fails."""

        sections = []

        for item in combined_result["successful_results"]:
            data = item["data"]

            if "findings" in data:
                findings = data.get("findings", [])

                for finding in findings:
                    title = finding.get("title", "Source")
                    snippet = finding.get("snippet", "")
                    url = finding.get("url", "")

                    sections.append(
                        f"### {title}\n"
                        f"{snippet}\n"
                        f"Source: {url}"
                    )

            elif "analysis" in data:
                sections.append(
                    f"### Code Analysis\n{data.get('analysis', '')}"
                )

            elif "rows" in data:
                sections.append(
                    f"### Database Results\n"
                    f"```text\n{data.get('rows', [])}\n```"
                )

        if not sections:
            return (
                "The workflow completed, but no usable results "
                "were available for synthesis."
            )

        return (
            "## Research Findings\n\n"
            + "\n\n".join(sections)
        )