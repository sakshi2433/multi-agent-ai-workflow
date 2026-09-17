"""Central configuration management."""
import os
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # LLM Configuration
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = "openai/gpt-3.5-turbo"
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    LLM_MODE: str = "offline"  # "online" or "offline"
    LLM_TIMEOUT_SECONDS: int = 30
    TAVILY_API_KEY: str = ""
    # Database Configuration
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/multi_agent_db"

    # Redis Configuration
    REDIS_URL: str = "redis://localhost:6379/0"

    # Workflow Configuration
    MAX_WORKFLOW_STEPS: int = 100
    WORKFLOW_BUDGET_LIMIT_USD: float = 10.0
    WORKFLOW_TIMEOUT_SECONDS: int = 300

    # Tool Configuration
    TOOL_TIMEOUT_SECONDS: int = 30
    MAX_RETRIES: int = 3
    RETRY_DELAY_SECONDS: int = 1
    
    # Approval Configuration
    APPROVAL_REQUIRED: bool = True

    # Logging
    LOG_LEVEL: str = "INFO"

    # Application
    APP_NAME: str = "multi-agent-workflow"
    APP_PORT: int = 8000
    
    class Config:
        env_file = ".env"


settings = Settings()