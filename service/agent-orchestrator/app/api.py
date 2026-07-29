import time

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.repositories import complete_agent_run, create_agent_run, fail_agent_run
from app.db.session import check_db_connection
from app.db.session import get_db
from app.graphs.workflow import WorkflowGraph
from app.states.workflow import WorkflowRequest, WorkflowResponse
from app.telemetry import reset_telemetry_context, set_telemetry_context, timed_ms
from app.tools import default_tool_registry


graph = WorkflowGraph()
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

    try:
        route, task_type, workflow_plan, summary, specialist_results, final_answer = graph.execute(
            payload.input_text
        )
        complete_agent_run(
            db=db,
            agent_run=agent_run,
            route=route.value,
            task_type=task_type.value,
            final_answer=final_answer,
            duration_ms=timed_ms(start_time),
        )
        return WorkflowResponse(
            trace_id=agent_run.trace_id,
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
