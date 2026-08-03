import time

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.repositories import complete_agent_run, create_agent_run, fail_agent_run
from app.db.session import check_db_connection
from app.db.session import get_db
from app.graphs.workflow import WorkflowGraph
from app.memory import ShortTermMemory, SupermemoryClient, resolve_reference
from app.states.workflow import WorkflowRequest, WorkflowResponse
from app.telemetry import reset_telemetry_context, set_telemetry_context, timed_ms
from app.tools import default_tool_registry


graph = WorkflowGraph()
memory_client = SupermemoryClient()
short_term_memory = ShortTermMemory()
router = APIRouter()


@router.get("/health")
def health_check():
    return {"status": "healthy", "service": "agent-orchestrator"}


@router.get("/tools")
def list_tools():
    return {"tools": default_tool_registry.list_tools()}


@router.get("/db/health")
def db_health_check():
    try:
        check_db_connection()
    except Exception as exc:
        return {
            "status": "unhealthy",
            "database": "postgresql",
            "error": str(exc),
        }
    return {"status": "healthy", "database": "postgresql"}


@router.post("/run", response_model=WorkflowResponse)
def run_workflow(payload: WorkflowRequest, db: Session = Depends(get_db)):
    start_time = time.perf_counter()
    agent_run = create_agent_run(db, payload.input_text)
    telemetry_tokens = set_telemetry_context(db, agent_run.id)
    memory_context_parts = []
    short_memory_context = short_term_memory.recall_context(
        user_id=payload.user_id,
        session_id=payload.session_id,
    )
    if short_memory_context:
        memory_context_parts.append(f"Recent session memory:\n{short_memory_context}")

    long_memory_context = memory_client.recall_context(
        query=payload.input_text,
        user_id=payload.user_id,
        session_id=payload.session_id,
    )
    if long_memory_context:
        memory_context_parts.append(long_memory_context)

    memory_context = "\n\n".join(memory_context_parts)
    resolved_input_text = resolve_reference(payload.input_text, memory_context)
    if resolved_input_text != payload.input_text:
        memory_context = (
            f"{memory_context}\n\n"
            f"Resolved user request: {resolved_input_text}"
        ).strip()

    try:
        route, task_type, workflow_plan, summary, specialist_results, final_answer = graph.execute(
            resolved_input_text,
            memory_context=memory_context,
        )
        complete_agent_run(
            db=db,
            agent_run=agent_run,
            route=route.value,
            task_type=task_type.value,
            final_answer=final_answer,
            duration_ms=timed_ms(start_time),
        )
        memory_client.remember_turn(
            input_text=payload.input_text,
            final_answer=final_answer,
            trace_id=agent_run.trace_id,
            user_id=payload.user_id,
            session_id=payload.session_id,
        )
        short_term_memory.remember_turn(
            input_text=payload.input_text,
            final_answer=final_answer,
            user_id=payload.user_id,
            session_id=payload.session_id,
        )
        return WorkflowResponse(
            trace_id=agent_run.trace_id,
            session_id=payload.session_id,
            user_id=payload.user_id,
            route=route,
            task_type=task_type,
            workflow_plan=workflow_plan,
            orchestrator_summary=summary,
            specialist_results=specialist_results,
            final_answer=final_answer,
        )
    except Exception as exc:
        fail_agent_run(
            db=db,
            agent_run=agent_run,
            error_message=str(exc),
            duration_ms=timed_ms(start_time),
        )
        raise
    finally:
        reset_telemetry_context(telemetry_tokens)
