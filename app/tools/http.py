"""HTTP/API tool for making external API requests."""
import asyncio
import logging
from typing import Any, Dict

import httpx

from app.tools.base import BaseTool


class HttpTool(BaseTool):
    """Tool for making HTTP requests."""

    name = "http_request"
    description = "Makes HTTP GET/POST requests to external APIs"

    def __init__(self):
        super().__init__(self.name, self.description)
        self.logger = logging.getLogger(__name__)

    async def _execute_tool(self, input_data: Dict[str, Any]) -> Any:
        """Execute HTTP request."""
        url = input_data.get("url", "")
        method = input_data.get("method", "GET")
        headers = input_data.get("headers", {})
        payload = input_data.get("payload")
        timeout = input_data.get("timeout", 30)

        # Validate URL
        if not url:
            raise ValueError("URL is required")

        # Security: Only allow http/https schemes
        if not url.startswith("http://") and not url.startswith("https://"):
            raise ValueError("URL must use http or https scheme")

        async with httpx.AsyncClient(timeout=timeout) as client:
            if method.upper() == "GET":
                response = await client.get(url, headers=headers)
            elif method.upper() == "POST":
                response = await client.post(url, headers=headers, json=payload)
            elif method.upper() == "PUT":
                response = await client.put(url, headers=headers, json=payload)
            elif method.upper() == "DELETE":
                response = await client.delete(url, headers=headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            return {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "body": response.text[:10000]  # Limit response size
            }