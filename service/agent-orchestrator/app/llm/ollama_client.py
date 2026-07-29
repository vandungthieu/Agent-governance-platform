from __future__ import annotations

import time

import httpx

from app.core.config import settings
from app.telemetry import record_model_call, timed_ms


class OllamaClient:
    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model = model or settings.OLLAMA_MODEL
        self.timeout_seconds = timeout_seconds or settings.LLM_TIMEOUT_SECONDS

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        start_time = time.perf_counter()
        try:
            response = httpx.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "stream": False,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                },
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
            response_text = payload.get("message", {}).get("content", "").strip()
            record_model_call(
                provider=settings.LLM_PROVIDER,
                model_name=self.model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_text=response_text,
                status="completed",
                duration_ms=timed_ms(start_time),
            )
            return response_text
        except Exception as exc:
            record_model_call(
                provider=settings.LLM_PROVIDER,
                model_name=self.model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_text=None,
                status="failed",
                duration_ms=timed_ms(start_time),
                error_message=str(exc),
            )
            raise
