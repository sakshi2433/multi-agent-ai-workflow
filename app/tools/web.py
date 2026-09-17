"""Web search tool for information gathering."""

import logging
from typing import Any, Dict

from tavily import TavilyClient

from app.tools.base import BaseTool
from app.core.config import settings


class WebSearchTool(BaseTool):
    """Tool for real web search using Tavily."""

    name = "web_search"
    description = "Performs real web searches and returns relevant results"

    def __init__(self):
        super().__init__(self.name, self.description)
        self.logger = logging.getLogger(__name__)

        api_key = getattr(settings, "TAVILY_API_KEY", None)

        if not api_key:
            raise ValueError(
                "TAVILY_API_KEY is not configured. "
                "Add it to your .env file."
            )

        self.client = TavilyClient(api_key=api_key)

    async def _execute_tool(
        self, input_data: Dict[str, Any]
    ) -> Any:
        """Execute a real web search."""

        query = input_data.get("query", "")
        max_results = input_data.get("max_results", 5)

        if not query:
            raise ValueError("Query cannot be empty")

        if max_results <= 0 or max_results > 20:
            raise ValueError(
                "max_results must be between 1 and 20"
            )

        try:
            response = self.client.search(
                query=query,
                max_results=max_results,
                search_depth="advanced",
                include_answer=False,
            )

            results = []

            for index, item in enumerate(
                response.get("results", []), start=1
            ):
                results.append(
                    {
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "snippet": item.get("content", ""),
                        "source": item.get("url", ""),
                        "rank": index,
                    }
                )

            return {
                "query": query,
                "results": results,
                "total_results": len(results),
            }

        except Exception as e:
            self.logger.error(
                f"Web search failed for '{query}': {e}"
            )
            raise