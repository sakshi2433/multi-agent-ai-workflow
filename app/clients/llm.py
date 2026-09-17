"""LLM client for agent communication with error handling."""

import json
import logging
from typing import Any, Dict, Optional

import httpx

from app.core.config import settings


class LLMClient:
    """Client for interacting with LLM providers via OpenRouter."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: int = 60,
        offline_mode: bool = False,
    ):
        """Initialize LLM client."""

        self.api_key = api_key or settings.OPENROUTER_API_KEY
        self.base_url = base_url or settings.OPENROUTER_BASE_URL
        self.model = model or settings.OPENROUTER_MODEL
        self.timeout = timeout
        self.offline_mode = offline_mode
        self.logger = logging.getLogger(__name__)

    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        json_mode: bool = False,
    ) -> Dict[str, Any]:
        """Generate a response from the LLM."""

        if self.offline_mode:
            return self._mock_response(prompt, json_mode)

        if not self.api_key:
            self.logger.error(
                "No API key provided and offline mode is disabled"
            )
            return {
                "success": False,
                "content": "",
                "error": "Missing API key",
            }

        url = f"{self.base_url.rstrip('/')}/chat/completions"

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if json_mode:
            payload["response_format"] = {
                "type": "json_object"
            }

        self.logger.info(
            f"[LLM] Requesting model={self.model}, "
            f"prompt_length={len(prompt)}, "
            f"max_tokens={max_tokens}"
        )

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout
            ) as client:

                response = await client.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": (
                            "https://github.com/"
                            "yourusername/"
                            "multi-agent-workflow"
                        ),
                        "X-Title": "Multi-Agent AI Workflow",
                    },
                    json=payload,
                )

            self.logger.info(
                f"[LLM] HTTP status: {response.status_code}"
            )

            if response.status_code != 200:
                error_msg = (
                    f"LLM API error: "
                    f"{response.status_code} - "
                    f"{response.text[:2000]}"
                )

                self.logger.error(error_msg)

                return {
                    "success": False,
                    "content": "",
                    "error": error_msg,
                }

            try:
                result = response.json()
            except json.JSONDecodeError as e:
                error_msg = (
                    f"Invalid JSON returned by LLM API: {e}"
                )

                self.logger.error(
                    f"{error_msg}. "
                    f"Response: {response.text[:1000]}"
                )

                return {
                    "success": False,
                    "content": "",
                    "error": error_msg,
                }

            choices = result.get("choices", [])

            if not choices:
                error_msg = (
                    "LLM API returned no choices"
                )

                self.logger.error(
                    f"{error_msg}. Response: "
                    f"{json.dumps(result)[:2000]}"
                )

                return {
                    "success": False,
                    "content": "",
                    "error": error_msg,
                }

            message = choices[0].get("message", {})
            content = message.get("content", "")

            if isinstance(content, list):
                # Some OpenRouter models may return
                # structured content blocks.
                content = "".join(
                    block.get("text", "")
                    for block in content
                    if isinstance(block, dict)
                )

            if not content or not str(content).strip():
                error_msg = (
                    "LLM API returned an empty content response"
                )

                self.logger.error(
                    f"{error_msg}. Response: "
                    f"{json.dumps(result)[:2000]}"
                )

                return {
                    "success": False,
                    "content": "",
                    "error": error_msg,
                }

            content = str(content).strip()

            self.logger.info(
                f"[LLM] Generation successful: "
                f"{len(content)} characters"
            )

            return {
                "success": True,
                "content": content,
                "model": self.model,
                "usage": result.get("usage", {}),
            }

        except httpx.TimeoutException:
            error_msg = (
                f"LLM request timeout after "
                f"{self.timeout} seconds"
            )

            self.logger.error(error_msg)

            return {
                "success": False,
                "content": "",
                "error": error_msg,
            }

        except httpx.RequestError as e:
            error_msg = f"LLM request error: {str(e)}"

            self.logger.error(error_msg)

            return {
                "success": False,
                "content": "",
                "error": error_msg,
            }

        except Exception as e:
            error_msg = (
                f"Unexpected error in LLM client: {str(e)}"
            )

            self.logger.exception(error_msg)

            return {
                "success": False,
                "content": "",
                "error": error_msg,
            }

    async def parse_json(
        self,
        prompt: str,
        expected_keys: Optional[list[str]] = None,
        temperature: float = 0.3,
    ) -> Dict[str, Any]:
        """Generate and parse a JSON response."""

        response = await self.generate(
            prompt=prompt,
            temperature=temperature,
            max_tokens=2000,
            json_mode=True,
        )

        if not response["success"]:
            return {
                "success": False,
                "data": {},
                "error": response.get(
                    "error",
                    "Generation failed",
                ),
            }

        try:
            content = response["content"].strip()

            if "```json" in content:
                content = (
                    content.split("```json", 1)[1]
                    .split("```", 1)[0]
                    .strip()
                )

            elif "```" in content:
                content = (
                    content.split("```", 1)[1]
                    .split("```", 1)[0]
                    .strip()
                )

            data = json.loads(content)

            if not isinstance(data, dict):
                return {
                    "success": False,
                    "data": {},
                    "error": (
                        "LLM JSON response is not an object"
                    ),
                }

            if expected_keys:
                missing_keys = [
                    key
                    for key in expected_keys
                    if key not in data
                ]

                if missing_keys:
                    return {
                        "success": False,
                        "data": data,
                        "error": (
                            "Missing keys in LLM response: "
                            f"{missing_keys}"
                        ),
                    }

            return {
                "success": True,
                "data": data,
            }

        except json.JSONDecodeError as e:
            return {
                "success": False,
                "data": {},
                "error": (
                    f"Failed to parse LLM JSON response: {e}"
                ),
            }

        except Exception as e:
            return {
                "success": False,
                "data": {},
                "error": (
                    f"Unexpected error parsing LLM response: {e}"
                ),
            }

    def _mock_response(
        self,
        prompt: str,
        json_mode: bool = False,
    ) -> Dict[str, Any]:
        """Generate a mock response for offline mode."""

        if json_mode:
            mock_content = json.dumps(
                {
                    "subtasks": [
                        {
                            "agent": "research",
                            "task": (
                                "Search for information "
                                "on the requested topic"
                            ),
                            "description": (
                                "Perform web search research"
                            ),
                        }
                    ]
                }
            )

            return {
                "success": True,
                "content": mock_content,
                "model": f"{self.model} (mock)",
            }

        return {
            "success": True,
            "content": (
                f"Mock response for: {prompt[:50]}..."
            ),
            "model": f"{self.model} (mock)",
        }


async def get_llm_client(
    offline_mode: Optional[bool] = None,
) -> LLMClient:
    """Factory function to get an LLM client instance."""

    mode = (
        offline_mode
        if offline_mode is not None
        else settings.LLM_MODE == "offline"
    )

    return LLMClient(offline_mode=mode)