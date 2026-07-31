from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import settings


logger = logging.getLogger("agent-orchestrator.memory")


class SupermemoryClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else settings.SUPERMEMORY_API_KEY
        self.base_url = (base_url or settings.SUPERMEMORY_BASE_URL).rstrip("/")
        self.timeout_seconds = timeout_seconds or settings.SUPERMEMORY_TIMEOUT_SECONDS

    @property
    def enabled(self) -> bool:
        return settings.SUPERMEMORY_ENABLED and bool(self.api_key)

    def container_tag(self, user_id: str | None, session_id: str | None) -> str | None:
        identity = user_id or session_id
        if not identity:
            return None
        return f"{settings.SUPERMEMORY_CONTAINER_PREFIX}:{identity}"

    def recall_context(
        self,
        query: str,
        user_id: str | None = None,
        session_id: str | None = None,
    ) -> str:
        container_tag = self.container_tag(user_id=user_id, session_id=session_id)
        if not self.enabled or not container_tag:
            return ""

        try:
            response = httpx.post(
                f"{self.base_url}/v4/profile",
                headers=self._headers(),
                json={"containerTag": container_tag, "q": query},
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            return self._format_profile_context(response.json())
        except Exception as exc:
            logger.warning("supermemory_recall_failed error=%s", exc)
            return ""

    def remember_turn(
        self,
        input_text: str,
        final_answer: str,
        trace_id: str,
        user_id: str | None = None,
        session_id: str | None = None,
    ) -> None:
        container_tag = self.container_tag(user_id=user_id, session_id=session_id)
        if not self.enabled or not container_tag:
            return

        conversation = f"user: {input_text}\nassistant: {final_answer}".strip()
        try:
            response = httpx.post(
                f"{self.base_url}/v3/documents",
                headers=self._headers(),
                json={
                    "content": conversation,
                    "containerTag": container_tag,
                    "customId": trace_id,
                    "metadata": {
                        "type": "conversation",
                        "source": "agent-orchestrator",
                        "session_id": session_id,
                        "user_id": user_id,
                    },
                    "dreaming": "instant",
                },
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
        except Exception as exc:
            logger.warning("supermemory_remember_failed trace_id=%s error=%s", trace_id, exc)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _format_profile_context(self, payload: dict[str, Any]) -> str:
        profile = payload.get("profile") or {}
        search_results = payload.get("searchResults") or payload.get("search_results") or {}
        lines: list[str] = []

        static_profile = profile.get("static") or []
        dynamic_profile = profile.get("dynamic") or []
        if static_profile:
            lines.append("Static profile:")
            lines.extend(f"- {item}" for item in static_profile)
        if dynamic_profile:
            lines.append("Recent memory:")
            lines.extend(f"- {item}" for item in dynamic_profile)

        results = search_results.get("results") if isinstance(search_results, dict) else None
        if results:
            lines.append("Relevant memories:")
            for result in results[:5]:
                memory = result.get("memory") or result.get("content") or result.get("text")
                if memory:
                    lines.append(f"- {memory}")

        return "\n".join(lines)
