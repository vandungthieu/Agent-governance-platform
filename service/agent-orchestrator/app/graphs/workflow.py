from __future__ import annotations

import time
from typing import Literal

from langgraph.graph import END, START, StateGraph

from app.agents.banking_knowledge_agent import BankingKnowledgeAgent
from app.agents.customer_data_guard_agent import CustomerDataGuardAgent
from app.agents.orchestrator_agent import OrchestratorAgent
from app.states.workflow import AgentRole, AgentState
from app.telemetry import record_workflow_step, reset_agent_role, set_agent_role, timed_ms


class WorkflowGraph:
    def __init__(self) -> None:
        self.orchestrator = OrchestratorAgent()
        self.customer_data_guard = CustomerDataGuardAgent()
        self.banking_knowledge = BankingKnowledgeAgent()
        self.graph = self._build()

    def _build(self):
        builder = StateGraph(AgentState)

        builder.add_node("orchestrator", self._orchestrator_node)
        builder.add_node("customer_data_guard", self._customer_data_guard_node)
        builder.add_node("banking_knowledge", self._banking_knowledge_node)
        builder.add_node("finalize", self._finalize_node)

        builder.add_edge(START, "orchestrator")
        builder.add_conditional_edges(
            "orchestrator",
            self._route,
            {
                "orchestrator": "finalize",
                "customer_data_guard": "customer_data_guard",
                "banking_knowledge": "banking_knowledge",
            },
        )
        builder.add_edge("customer_data_guard", "finalize")
        builder.add_edge("banking_knowledge", "finalize")
        builder.add_edge("finalize", END)

        return builder.compile()

    def _orchestrator_node(self, state: AgentState) -> dict:
        start_time = time.perf_counter()
        role_token = set_agent_role(AgentRole.orchestrator.value)
        try:
            route = AgentRole(self.orchestrator.route(state.input_text))
            task_type = self.orchestrator.classify_task(state.input_text)
            node_output = {
                "route": route,
                "task_type": task_type,
                "workflow_plan": self.orchestrator.build_plan(state.input_text),
                "orchestrator_summary": self.orchestrator.run(
                    state.input_text,
                    memory_context=state.memory_context,
                ),
            }
            if route == AgentRole.orchestrator:
                node_output["final_answer"] = self.orchestrator.answer_direct(
                    state.input_text,
                    memory_context=state.memory_context,
                )
            record_workflow_step(
                step_name="orchestrator_classify",
                agent_role=AgentRole.orchestrator.value,
                task_type=task_type.value,
                status="completed",
                input_preview=state.input_text,
                output_preview=node_output,
                duration_ms=timed_ms(start_time),
            )
            return node_output
        except Exception as exc:
            record_workflow_step(
                step_name="orchestrator_classify",
                agent_role=AgentRole.orchestrator.value,
                task_type=None,
                status="failed",
                input_preview=state.input_text,
                output_preview=str(exc),
                duration_ms=timed_ms(start_time),
            )
            raise
        finally:
            reset_agent_role(role_token)

    def _customer_data_guard_node(self, state: AgentState) -> dict:
        start_time = time.perf_counter()
        role_token = set_agent_role(AgentRole.customer_data_guard.value)
        try:
            node_output = {
                "specialist_results": [
                    {
                        "role": AgentRole.customer_data_guard,
                        "task_type": state.task_type,
                        "output": self.customer_data_guard.run(
                            state.input_text,
                            state.task_type,
                            memory_context=state.memory_context,
                        ),
                    }
                ]
            }
            record_workflow_step(
                step_name="customer_data_guard_run",
                agent_role=AgentRole.customer_data_guard.value,
                task_type=state.task_type.value,
                status="completed",
                input_preview=state.input_text,
                output_preview=node_output,
                duration_ms=timed_ms(start_time),
            )
            return node_output
        except Exception as exc:
            record_workflow_step(
                step_name="customer_data_guard_run",
                agent_role=AgentRole.customer_data_guard.value,
                task_type=state.task_type.value,
                status="failed",
                input_preview=state.input_text,
                output_preview=str(exc),
                duration_ms=timed_ms(start_time),
            )
            raise
        finally:
            reset_agent_role(role_token)

    def _banking_knowledge_node(self, state: AgentState) -> dict:
        start_time = time.perf_counter()
        role_token = set_agent_role(AgentRole.banking_knowledge.value)
        try:
            node_output = {
                "specialist_results": [
                    {
                        "role": AgentRole.banking_knowledge,
                        "task_type": state.task_type,
                        "output": self.banking_knowledge.run(
                            state.input_text,
                            state.task_type,
                            memory_context=state.memory_context,
                        ),
                    }
                ]
            }
            record_workflow_step(
                step_name="banking_knowledge_run",
                agent_role=AgentRole.banking_knowledge.value,
                task_type=state.task_type.value,
                status="completed",
                input_preview=state.input_text,
                output_preview=node_output,
                duration_ms=timed_ms(start_time),
            )
            return node_output
        except Exception as exc:
            record_workflow_step(
                step_name="banking_knowledge_run",
                agent_role=AgentRole.banking_knowledge.value,
                task_type=state.task_type.value,
                status="failed",
                input_preview=state.input_text,
                output_preview=str(exc),
                duration_ms=timed_ms(start_time),
            )
            raise
        finally:
            reset_agent_role(role_token)

    def _finalize_node(self, state: AgentState) -> dict:
        start_time = time.perf_counter()
        try:
            if state.route == AgentRole.orchestrator and state.final_answer:
                node_output = {"final_answer": state.final_answer}
                record_workflow_step(
                    step_name="finalize",
                    agent_role=AgentRole.orchestrator.value,
                    task_type=state.task_type.value,
                    status="completed",
                    input_preview=state.input_text,
                    output_preview=node_output,
                    duration_ms=timed_ms(start_time),
                )
                return node_output

            specialist_output = state.specialist_results[0].output if state.specialist_results else ""
            final_answer = specialist_output or state.orchestrator_summary
            node_output = {"final_answer": final_answer}
            record_workflow_step(
                step_name="finalize",
                agent_role=state.route.value,
                task_type=state.task_type.value,
                status="completed",
                input_preview=state.input_text,
                output_preview=node_output,
                duration_ms=timed_ms(start_time),
            )
            return node_output
        except Exception as exc:
            record_workflow_step(
                step_name="finalize",
                agent_role=state.route.value,
                task_type=state.task_type.value,
                status="failed",
                input_preview=state.input_text,
                output_preview=str(exc),
                duration_ms=timed_ms(start_time),
            )
            raise

    def _route(self, state: AgentState) -> Literal["orchestrator", "customer_data_guard", "banking_knowledge"]:
        if state.route == AgentRole.orchestrator:
            return "orchestrator"
        if state.route == AgentRole.customer_data_guard:
            return "customer_data_guard"
        return "banking_knowledge"

    def execute(
        self,
        input_text: str,
        memory_context: str = "",
    ) -> tuple[AgentRole, object, list[str], str, list, str]:
        result = self.graph.invoke({"input_text": input_text, "memory_context": memory_context})
        return (
            result["route"],
            result["task_type"],
            result["workflow_plan"],
            result["orchestrator_summary"],
            result["specialist_results"],
            result["final_answer"],
        )
