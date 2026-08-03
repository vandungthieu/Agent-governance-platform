from __future__ import annotations

import httpx

from app.core.config import settings


class TelegramClient:
    def __init__(self) -> None:
        self.token = settings.TELEGRAM_BOT_TOKEN
        self.timeout = settings.HTTP_TIMEOUT_SECONDS

    @property
    def base_url(self) -> str:
        return f"https://api.telegram.org/bot{self.token}"

    async def send_message(self, *, chat_id: int | str, text: str) -> None:
        if not self.token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "disable_web_page_preview": True,
                },
            )
            response.raise_for_status()
