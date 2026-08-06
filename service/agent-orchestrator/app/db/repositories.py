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
    intent: str | None,
    intent_confidence: float | None,
    routing_source: str | None,
    retrieval_document_type: str | None,
    routing_reason: str | None,
    matched_example: str | None,
    semantic_candidates: list[dict] | None,
    llm_planner_output: str | None,
    final_answer: str,
    duration_ms: float,
) -> AgentRun:
    agent_run.route = route
    agent_run.task_type = task_type
    agent_run.intent = intent
    agent_run.intent_confidence = intent_confidence
    agent_run.routing_source = routing_source
    agent_run.retrieval_document_type = retrieval_document_type
    agent_run.routing_reason = routing_reason
    agent_run.matched_example = matched_example
    agent_run.semantic_candidates = semantic_candidates
    agent_run.llm_planner_output = llm_planner_output
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
