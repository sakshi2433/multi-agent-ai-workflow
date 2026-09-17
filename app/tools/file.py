"""File inspection tool for safe file operations."""
import asyncio
import hashlib
import logging
import os
from typing import Any, Dict

from app.tools.base import BaseTool


class FileTool(BaseTool):
    """Tool for safe file inspection."""

    name = "file_inspector"
    description = "Inspects files for metadata and content"

    def __init__(self):
        super().__init__(self.name, self.description)
        self.logger = logging.getLogger(__name__)

    async def _execute_tool(self, input_data: Dict[str, Any]) -> Any:
        """Inspect a file safely."""
        file_path = input_data.get("path", "")
        max_size = input_data.get("max_size", 1024 * 1024)  # 1MB default
        allowed_extensions = input_data.get("allowed_extensions", [".txt", ".json", ".csv", ".log", ".py"])

        # Validate path
        if not file_path:
            raise ValueError("Path is required")

        # Safety: Prevent reading sensitive files
        dangerous_paths = ["/etc/passwd", "/etc/shadow", "/root", "id_rsa", ".env"]
        for dangerous in dangerous_paths:
            if dangerous in file_path:
                raise ValueError(f"Access to sensitive path denied: {file_path}")

        # Check extension
        _, ext = os.path.splitext(file_path)
        if ext.lower() not in allowed_extensions:
            raise ValueError(f"File extension not allowed: {ext}")

        # Check if file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        # Check file size
        file_size = os.path.getsize(file_path)
        if file_size > max_size:
            raise ValueError(f"File too large: {file_size} bytes (max: {max_size})")

        await asyncio.sleep(0.05)  # Simulate I/O

        # Read file content
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            # Try reading as binary for non-text files
            with open(file_path, "rb") as f:
                content = f.read(max_size)
                content = f"<binary content, size: {len(content)} bytes>"

        # Calculate hash
        content_hash = hashlib.sha256(content.encode() if isinstance(content, str) else content).hexdigest()

        return {
            "path": file_path,
            "size": file_size,
            "extension": ext,
            "hash": content_hash,
            "content_preview": content[:1000] if isinstance(content, str) else None,
            "success": True
        }