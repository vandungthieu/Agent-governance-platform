from __future__ import annotations

from typing import Any

import httpx

from app.core.config import settings


class AgentClient:
    def __init__(self) -> None:
        self.api_url = settings.AGENT_API_URL
        self.timeout = settings.HTTP_TIMEOUT_SECONDS
        self.bearer_token = settings.AGENT_API_BEARER_TOKEN

    async def run(self, *, input_text: str, session_id: str, user_id: str) -> str:
        headers: dict[str, str] = {}
        if self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"

        payload = {
            "input_text": input_text,
            "session_id": session_id,
            "user_id": user_id,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(self.api_url, json=payload, headers=headers)
            response.raise_for_status()
            data: dict[str, Any] = response.json()

        return str(data.get("final_answer") or "No answer was returned by the agent.")
