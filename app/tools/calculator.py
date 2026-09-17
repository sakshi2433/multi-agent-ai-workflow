"""Calculator tool for mathematical calculations."""
import asyncio
from typing import Any, Dict

from app.tools.base import BaseTool


class CalculatorTool(BaseTool):
    """Tool for performing mathematical calculations."""

    name = "calculator"
    description = "Performs mathematical calculations"

    def __init__(self):
        super().__init__(self.name, self.description)
        self.logger = None

    async def _execute_tool(self, input_data: Dict[str, Any]) -> Any:
        """Perform calculation based on input_data."""
        operation = input_data.get("operation", "add")
        a = input_data.get("a", 0)
        b = input_data.get("b", 0)

        if operation == "add":
            return a + b
        elif operation == "subtract":
            return a - b
        elif operation == "multiply":
            return a * b
        elif operation == "divide":
            if b == 0:
                raise ZeroDivisionError("Cannot divide by zero")
            return a / b
        else:
            raise ValueError(f"Unsupported operation: {operation}")