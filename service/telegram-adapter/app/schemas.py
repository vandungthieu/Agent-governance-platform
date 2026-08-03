from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class TelegramUser(BaseModel):
    id: int
    is_bot: bool | None = None
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None


class TelegramChat(BaseModel):
    id: int
    type: str
    title: str | None = None
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None


class TelegramMessage(BaseModel):
    message_id: int
    from_user: TelegramUser | None = Field(default=None, alias="from")
    chat: TelegramChat
    text: str | None = None


class TelegramUpdate(BaseModel):
    update_id: int
    message: TelegramMessage | None = None
    edited_message: TelegramMessage | None = None
    callback_query: dict[str, Any] | None = None

    def effective_message(self) -> TelegramMessage | None:
        return self.message or self.edited_message
