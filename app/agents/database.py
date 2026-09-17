"""Database agent for safe PostgreSQL queries."""
import asyncio
import logging
from typing import Any, Dict

from app.tools.base import BaseTool, ToolResponse


class DatabaseAgent:
    """Agent for safe database operations with typed parameters."""

    name = "database_agent"
    description = "Executes safe SQL queries on PostgreSQL database"

    def __init__(self, db_tool: BaseTool | None = None):
        self.db_tool = db_tool or self._create_default_db_tool()
        self.logger = logging.getLogger(__name__)

    def _create_default_db_tool(self) -> BaseTool:
        """Create a default database tool (simulated for testing)."""
        class DefaultDBTool(BaseTool):
            name = "database_query"
            description = "Simulated PostgreSQL query tool"

            async def _execute_tool(self, input_data: Dict[str, Any]) -> Any:
                query = input_data.get("query", "")
                await asyncio.sleep(0.1)  # Simulate query execution
                
                # Validate query safety
                dangerous_keywords = ["drop", "delete", "truncate", "alter", "update", "insert"]
                for keyword in dangerous_keywords:
                    if keyword in query.lower():
                        raise ValueError(f"Unsafe SQL operation detected: {keyword}")

                # Simulate query result
                return {
                    "query": query,
                    "rows": [
                        {"id": 1, "name": "Sample Row 1", "value": "test"},
                        {"id": 2, "name": "Sample Row 2", "value": "demo"}
                    ],
                    "row_count": 2
                }

        return DefaultDBTool("database_query", "Simulated PostgreSQL query tool")

    async def query(self, query: str) -> Dict[str, Any]:
        """Execute a safe database query."""
        self.logger.info(f"Database agent executing query: {query}")

        try:
            result = await self.db_tool.execute({"query": query})

            if result.status == "success":
                return {
                    "success": True,
                    "query": query,
                    "rows": result.output_data.get("rows", []),
                    "row_count": result.output_data.get("row_count", 0),
                    "error": None
                }
            else:
                return {
                    "success": False,
                    "query": query,
                    "rows": [],
                    "row_count": 0,
                    "error": result.error or "Query failed"
                }

        except Exception as e:
            self.logger.error(f"Database agent error: {e}")
            return {
                "success": False,
                "query": query,
                "rows": [],
                "row_count": 0,
                "error": str(e)
            }

    async def read_only_query(self, query: str) -> Dict[str, Any]:
        """Execute a read-only database query."""
        self.logger.info(f"Database agent executing read-only query: {query}")

        try:
            # Additional safety checks for read-only
            write_keywords = ["insert", "update", "delete", "drop", "alter", "truncate"]
            for keyword in write_keywords:
                if keyword in query.lower():
                    raise ValueError(f"Write operation not allowed: {keyword}")

            return await self.query(query)

        except Exception as e:
            self.logger.error(f"Database agent read-only error: {e}")
            return {
                "success": False,
                "query": query,
                "rows": [],
                "row_count": 0,
                "error": str(e)
            }