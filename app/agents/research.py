"""Research agent for web searches and information gathering."""

import logging
from typing import Any, Dict

from app.tools.base import BaseTool
from app.tools.web import WebSearchTool


class ResearchAgent:
    """Agent specialized in real web research."""

    name = "research_agent"
    description = (
        "Performs real web searches and gathers "
        "relevant information from online sources"
    )

    def __init__(self, search_tool: BaseTool | None = None):
        self.search_tool = search_tool or WebSearchTool()
        self.logger = logging.getLogger(__name__)

    async def research(self, query: str) -> Dict[str, Any]:
        """Perform real research on the given query."""

        self.logger.info(
            f"[RESEARCH] Searching the web for: {query}"
        )

        try:
            result = await self.search_tool.execute(
                {
                    "query": query,
                    "max_results": 5,
                }
            )

            if result.status == "success":
                findings = result.output_data.get(
                    "results", []
                )

                self.logger.info(
                    f"[RESEARCH] Found {len(findings)} results"
                )

                return {
                    "success": True,
                    "query": query,
                    "findings": findings,
                    "total_results": len(findings),
                    "error": None,
                }

            return {
                "success": False,
                "query": query,
                "findings": [],
                "total_results": 0,
                "error": result.error or "Search failed",
            }

        except Exception as e:
            self.logger.error(
                f"[RESEARCH] Error: {e}"
            )

            return {
                "success": False,
                "query": query,
                "findings": [],
                "total_results": 0,
                "error": str(e),
            }