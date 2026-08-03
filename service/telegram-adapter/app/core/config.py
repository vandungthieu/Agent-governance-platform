from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "telegram-adapter"
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_WEBHOOK_SECRET: str = ""
    AGENT_API_URL: str = "http://agent-orchestrator:8000/api/v1/run"
    AGENT_API_BEARER_TOKEN: str = ""
    HTTP_TIMEOUT_SECONDS: int = 300

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
