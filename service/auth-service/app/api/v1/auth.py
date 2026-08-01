from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_jwt,
    hash_password,
    hash_token,
    verify_password,
)
from app.database.db import get_db
from app.database.refresh_token import RefreshToken
from app.database.user import User
from app.schemas.auth import (
    IntrospectRequest,
    IntrospectResponse,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    TokenPair,
)
from app.schemas.user import UserCreate, UserPublic


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenPair, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> TokenPair:
    email = normalize_email(payload.email)
    existing_user = db.scalar(select(User).where(User.email == email))
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = User(
        email=email,
        full_name=payload.full_name.strip(),
        password_hash=hash_password(payload.password),
        role=payload.role or settings.DEFAULT_USER_ROLE,
        scopes=scopes_to_string(payload.scopes) if payload.scopes is not None else settings.DEFAULT_USER_SCOPES,
    )
    db.add(user)
    db.flush()
    token_pair = issue_token_pair(db, user)
    db.commit()
    db.refresh(user)
    return token_pair


@router.post("/login", response_model=TokenPair)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenPair:
    user = db.scalar(select(User).where(User.email == normalize_email(payload.email)))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive",
        )

    token_pair = issue_token_pair(db, user)
    db.commit()
    return token_pair


@router.post("/refresh", response_model=TokenPair)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> TokenPair:
    current_token = db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == hash_token(payload.refresh_token))
    )
    if current_token is None or current_token.revoked_at is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
    if current_token.expires_at < datetime.now(UTC):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired",
        )

    user = db.get(User, current_token.user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is inactive or no longer exists",
        )

    new_token_pair = issue_token_pair(db, user)
    current_token.revoked_at = datetime.now(UTC)
    current_token.replaced_by_token_id = db.scalar(
        select(RefreshToken.id).where(RefreshToken.user_id == user.id).order_by(RefreshToken.created_at.desc())
    )
    db.commit()
    return new_token_pair


@router.post("/logout")
def logout(payload: LogoutRequest, db: Session = Depends(get_db)) -> dict[str, bool]:
    refresh_token = db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == hash_token(payload.refresh_token))
    )
    if refresh_token is not None and refresh_token.revoked_at is None:
        refresh_token.revoked_at = datetime.now(UTC)
        db.commit()
    return {"revoked": True}


@router.get("/me", response_model=UserPublic)
def me(current_user: User = Depends(get_current_user)) -> UserPublic:
    return user_to_public(current_user)


@router.post("/introspect", response_model=IntrospectResponse)
def introspect(payload: IntrospectRequest) -> IntrospectResponse:
    try:
        claims = decode_jwt(payload.token)
    except ValueError:
        return IntrospectResponse(active=False)

    return IntrospectResponse(
        active=True,
        sub=claims.get("sub"),
        email=claims.get("email"),
        role=claims.get("role"),
        scopes=claims.get("scopes") or [],
    )


def issue_token_pair(db: Session, user: User) -> TokenPair:
    refresh_token, refresh_token_hash, expires_at = create_refresh_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=refresh_token_hash,
            expires_at=expires_at,
        )
    )
    db.flush()
    access_token = create_access_token(
        subject=str(user.id),
        email=user.email,
        role=user.role,
        scopes=string_to_scopes(user.scopes),
    )
    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=user_to_public(user),
    )


def normalize_email(email: str) -> str:
    return email.strip().lower()


def scopes_to_string(scopes: list[str]) -> str:
    return " ".join(scope.strip() for scope in scopes if scope.strip())


def string_to_scopes(scopes: str) -> list[str]:
    return [scope for scope in scopes.split() if scope]


def user_to_public(user: User) -> UserPublic:
    return UserPublic(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        scopes=string_to_scopes(user.scopes),
        is_active=user.is_active,
    )
