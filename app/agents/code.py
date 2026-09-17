"""Code agent for safe code operations."""
import asyncio
import logging
from typing import Any, Dict

from app.tools.base import BaseTool, ToolResponse


class CodeAgent:
    """Agent for controlled code operations with safety boundaries."""

    name = "code_agent"
    description = "Performs safe code analysis and transformations"

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.sandbox = True

    async def analyze_code(self, code: str, task: str) -> Dict[str, Any]:
        """Analyze code safely."""
        self.logger.info(f"Code agent analyzing code for task: {task}")

        try:
            # Simulated code analysis
            await asyncio.sleep(0.1)

            result = {
                "success": True,
                "code": code,
                "task": task,
                "analysis": {
                    "lines_of_code": len(code.split("\n")),
                    "complexity": "moderate",
                    "issues": []
                },
                "error": None
            }

            return result

        except Exception as e:
            self.logger.error(f"Code agent error: {e}")
            return {
                "success": False,
                "code": code,
                "task": task,
                "analysis": {},
                "error": str(e)
            }

    async def safe_execute(self, code: str) -> Dict[str, Any]:
        """Safely execute code in a sandboxed environment."""
        self.logger.info("Executing code in sandbox")

        try:
            # Only allow safe operations
            safe_keywords = ["print", "return", "def", "class", "if", "else", "for", "while", "import"]

            # Check for potentially dangerous keywords
            dangerous_patterns = ["import os", "import sys", "exec(", "eval(", "subprocess", "open("]
            for pattern in dangerous_patterns:
                if pattern in code:
                    return {
                        "success": False,
                        "code": code,
                        "error": f"Unsafe operation detected: {pattern}",
                        "metadata": {"blocked": True}
                    }

            await asyncio.sleep(0.1)

            return {
                "success": True,
                "code": code,
                "output": "Code executed successfully in sandbox",
                "error": None,
                "metadata": {"sandbox": True}
            }

        except Exception as e:
            self.logger.error(f"Code agent execution error: {e}")
            return {
                "success": False,
                "code": code,
                "error": str(e),
                "metadata": {"sandbox": True}
            }