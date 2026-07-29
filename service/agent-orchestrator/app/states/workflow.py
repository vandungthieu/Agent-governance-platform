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


class WorkflowRequest(BaseModel):
    input_text: str = Field(min_length=1)


class AgentResult(BaseModel):
    role: AgentRole
    task_type: TaskType
    output: str


def _merge_results(left: list["AgentResult"], right: list["AgentResult"]) -> list["AgentResult"]:
    return left + right


class AgentState(BaseModel):
    input_text: str
    route: AgentRole = AgentRole.orchestrator
    task_type: TaskType = TaskType.orchestrator_direct_response
    workflow_plan: list[str] = Field(default_factory=list)
    orchestrator_summary: str = ""
    specialist_results: Annotated[list[AgentResult], _merge_results] = Field(default_factory=list)
    final_answer: str = ""


class WorkflowResponse(BaseModel):
    trace_id: str
    route: AgentRole
    task_type: TaskType
    workflow_plan: list[str]
    orchestrator_summary: str
    specialist_results: list[AgentResult]
    final_answer: str
