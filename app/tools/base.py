"""Base class for all tools in the multi-agent system."""
import asyncio
import logging
import time
from enum import Enum
from typing import Any, Dict, Optional, Protocol

from pydantic import BaseModel, Field


class ToolError(Exception):
    """Custom exception for tool errors."""
    pass


class ToolResponse(BaseModel):
    """Standard response format for all tools."""
    tool_name: str = Field(..., description="Name of the tool called")
    status: str = Field(..., description="Status of the tool execution")
    output_data: Any = Field(..., description="Result data from the tool")
    error: Optional[str] = Field(None, description="Error message if any")
    execution_time_ms: float = Field(0.0, description="Execution time in milliseconds")
    retry_count: int = Field(0, description="Number of retries attempted")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ToolStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"


class ToolBase(Protocol):
    """Protocol defining the tool interface."""
    async def execute(self, input_data: Dict[str, Any]) -> ToolResponse:
        """Execute the tool with the given input data."""
        ...


class BaseTool:
    """Base implementation for all tools."""
    name: str = ""
    description: str = ""
    timeout_seconds: int = 30
    max_retries: int = 3
    retry_delay_seconds: int = 1

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    async def execute(self, input_data: Dict[str, Any]) -> ToolResponse:
        """Execute the tool with retry logic."""
        start_time = time.time()
        last_error = None

        for attempt in range(1, self.max_retries + 1):
            try:
                # Log attempt
                logging.debug(f"[{self.name}] Attempt {attempt}/{self.max_retries} with input: {input_data}")

                # Execute the tool
                result = await self._execute_tool(input_data)

                # Check for success
                if result is not None:
                    execution_time = (time.time() - start_time) * 1000
                    return ToolResponse(
                        tool_name=self.name,
                        status=ToolStatus.SUCCESS,
                        output_data=result,
                        execution_time_ms=execution_time,
                        retry_count=attempt - 1,
                        metadata={"attempt": attempt}
                    )

            except Exception as e:
                last_error = str(e)
                logging.error(f"[{self.name}] Attempt {attempt} failed: {e}")
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay_seconds)
                    continue

        # If we get here, all attempts failed
        execution_time = (time.time() - start_time) * 1000
        return ToolResponse(
            tool_name=self.name,
            status=ToolStatus.FAILED,
            output_data=None,
            error=str(last_error) if last_error else "Unknown error",
            execution_time_ms=execution_time,
            retry_count=attempt - 1,
            metadata={"attempt": attempt}
        )

    async def _execute_tool(self, input_data: Dict[str, Any]) -> Any:
        """Implement this method in subclasses to perform actual tool execution."""
        raise NotImplementedError(f"Subclass must implement _execute_tool for {self.name}")


class CalculatorTool(BaseTool):
    """Tool for performing mathematical calculations."""
    name: str = "calculator"
    description: str = "Performs mathematical calculations"

    def __init__(self):
        super().__init__(self.name, self.description)

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