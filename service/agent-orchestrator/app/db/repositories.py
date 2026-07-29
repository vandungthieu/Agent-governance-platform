import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.db.models import AgentRun


def create_agent_run(db: Session, input_text: str) -> AgentRun:
    agent_run = AgentRun(
        trace_id=f"tr_{uuid.uuid4().hex}",
        input_text=input_text,
        status="running",
        started_at=datetime.now(UTC),
    )
    db.add(agent_run)
    db.commit()
    db.refresh(agent_run)
    return agent_run


def complete_agent_run(
    db: Session,
    agent_run: AgentRun,
    route: str,
    task_type: str,
    final_answer: str,
    duration_ms: float,
) -> AgentRun:
    agent_run.route = route
    agent_run.task_type = task_type
    agent_run.final_answer = final_answer
    agent_run.status = "completed"
    agent_run.duration_ms = duration_ms
    agent_run.finished_at = datetime.now(UTC)
    db.commit()
    db.refresh(agent_run)
    return agent_run


def fail_agent_run(
    db: Session,
    agent_run: AgentRun,
    error_message: str,
    duration_ms: float,
) -> AgentRun:
    agent_run.status = "failed"
    agent_run.error_message = error_message
    agent_run.duration_ms = duration_ms
    agent_run.finished_at = datetime.now(UTC)
    db.commit()
    db.refresh(agent_run)
    return agent_run

