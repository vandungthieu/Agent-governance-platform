from __future__ import annotations

import json
import logging
import time
import uuid
from contextvars import ContextVar, Token
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import ModelCall, ToolCall, WorkflowStep


logger = logging.getLogger("agent-orchestrator.telemetry")

_current_db: ContextVar[Session | None] = ContextVar("current_db", default=None)
_current_agent_run_id: ContextVar[uuid.UUID | None] = ContextVar("current_agent_run_id", default=None)
_current_agent_role: ContextVar[str | None] = ContextVar("current_agent_role", default=None)


def set_telemetry_context(db: Session, agent_run_id: uuid.UUID) -> tuple[Token, Token]:
    return (
        _current_db.set(db),
        _current_agent_run_id.set(agent_run_id),
    )


def reset_telemetry_context(tokens: tuple[Token, Token]) -> None:
    db_token, run_token = tokens
    _current_db.reset(db_token)
    _current_agent_run_id.reset(run_token)


def set_agent_role(agent_role: str | None) -> Token:
    return _current_agent_role.set(agent_role)


def reset_agent_role(token: Token) -> None:
    _current_agent_role.reset(token)


def current_agent_role() -> str | None:
    return _current_agent_role.get()


def record_workflow_step(
    step_name: str,
    agent_role: str | None,
    task_type: str | None,
    status: str,
    input_preview: str | None,
    output_preview: str | None,
    duration_ms: float,
) -> None:
    db = _current_db.get()
    agent_run_id = _current_agent_run_id.get()
    if db is None or agent_run_id is None:
        return

    _safe_write(
        db,
        WorkflowStep(
            agent_run_id=agent_run_id,
            step_name=step_name,
            agent_role=agent_role,
            task_type=task_type,
            status=status,
            input_preview=_preview(input_preview),
            output_preview=_preview(output_preview),
            duration_ms=duration_ms,
            started_at=datetime.now(UTC),
            finished_at=datetime.now(UTC),
        ),
    )


def record_model_call(
    provider: str,
    model_name: str,
    system_prompt: str,
    user_prompt: str,
    response_text: str | None,
    status: str,
    duration_ms: float,
    error_message: str | None = None,
) -> None:
    db = _current_db.get()
    agent_run_id = _current_agent_run_id.get()
    if db is None or agent_run_id is None:
        return

    prompt_preview = f"system: {system_prompt}\n\nuser: {user_prompt}"
    _safe_write(
        db,
        ModelCall(
            agent_run_id=agent_run_id,
            agent_role=current_agent_role(),
            provider=provider,
            model_name=model_name,
            prompt_preview=_preview(prompt_preview),
            response_preview=_preview(response_text),
            status=status,
            error_message=_preview(error_message),
            duration_ms=duration_ms,
        ),
    )


def record_tool_call(
    tool_name: str,
    input_json: dict[str, Any],
    output_json: Any,
    status: str,
    duration_ms: float,
    error_message: str | None = None,
) -> None:
    db = _current_db.get()
    agent_run_id = _current_agent_run_id.get()
    if db is None or agent_run_id is None:
        return

    _safe_write(
        db,
        ToolCall(
            agent_run_id=agent_run_id,
            tool_name=tool_name,
            input_json=_json_safe(input_json),
            output_json=_json_safe(output_json),
            status=status,
            error_message=_preview(error_message),
            duration_ms=duration_ms,
        ),
    )


def timed_ms(start_time: float) -> float:
    return (time.perf_counter() - start_time) * 1000


def _preview(value: Any, limit: int = 2000) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text[:limit]


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, default=str, ensure_ascii=False))


def _safe_write(db: Session, row: Any) -> None:
    try:
        db.add(row)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("failed_to_write_telemetry table=%s", row.__tablename__)
