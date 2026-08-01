from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)
    role: str | None = Field(default=None, max_length=64)
    scopes: list[str] | None = None


class UserPublic(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: str
    scopes: list[str]
    is_active: bool

    model_config = {"from_attributes": True}
