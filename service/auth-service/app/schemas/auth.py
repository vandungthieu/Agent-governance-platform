from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.user import UserPublic


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=128)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserPublic


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=32)


class LogoutRequest(BaseModel):
    refresh_token: str = Field(min_length=32)


class IntrospectRequest(BaseModel):
    token: str = Field(min_length=16)


class IntrospectResponse(BaseModel):
    active: bool
    sub: str | None = None
    email: str | None = None
    role: str | None = None
    scopes: list[str] = []
