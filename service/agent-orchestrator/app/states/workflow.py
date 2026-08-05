from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field


class AgentRole(str, Enum):
    orchestrator = "orchestrator"
    customer_data_guard = "customer_data_guard"
    banking_knowledge = "banking_knowledge"


class TaskType(str, Enum):
    orchestrator_direct_response = "orchestrator_direct_response"
    customer_data_masking = "customer_data_masking"
    customer_profile_review = "customer_profile_review"
    document_intelligence = "document_intelligence"
    research_report = "research_report"
    banking_process_support = "banking_process_support"
    credit_risk_support = "credit_risk_support"
    general_banking_knowledge = "general_banking_knowledge"


class IntentType(str, Enum):
    customer_lookup = "customer_lookup"
    masking_request = "masking_request"
    banking_faq = "banking_faq"
    owner_question = "owner_question"
    realtime_web = "realtime_web"
    document_intelligence = "document_intelligence"
    research_report = "research_report"
    credit_risk = "credit_risk"
    smalltalk = "smalltalk"
    unknown = "unknown"


class RoutingDecision(BaseModel):
    intent: IntentType = IntentType.unknown
    route: AgentRole = AgentRole.orchestrator
    task_type: TaskType = TaskType.orchestrator_direct_response
    document_type: str | None = None
    confidence: float = 0.0
    routing_source: str = "fallback"
    reason: str = ""


class WorkflowRequest(BaseModel):
    input_text: str = Field(min_length=1)
    session_id: str | None = None
    user_id: str | None = None


class AgentResult(BaseModel):
    role: AgentRole
    task_type: TaskType
    output: str


def _merge_results(left: list["AgentResult"], right: list["AgentResult"]) -> list["AgentResult"]:
    return left + right


class AgentState(BaseModel):
    input_text: str
    memory_context: str = ""
    route: AgentRole = AgentRole.orchestrator
    task_type: TaskType = TaskType.orchestrator_direct_response
    intent: IntentType = IntentType.unknown
    intent_confidence: float = 0.0
    routing_source: str = "fallback"
    retrieval_document_type: str | None = None
    workflow_plan: list[str] = Field(default_factory=list)
    orchestrator_summary: str = ""
    specialist_results: Annotated[list[AgentResult], _merge_results] = Field(default_factory=list)
    final_answer: str = ""


class WorkflowResponse(BaseModel):
    trace_id: str
    session_id: str | None = None
    user_id: str | None = None
    route: AgentRole
    task_type: TaskType
    intent: IntentType = IntentType.unknown
    intent_confidence: float = 0.0
    routing_source: str = "fallback"
    retrieval_document_type: str | None = None
    workflow_plan: list[str]
    orchestrator_summary: str
    specialist_results: list[AgentResult]
    final_answer: str
