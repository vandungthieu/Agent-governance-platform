from __future__ import annotations

import json
import re
from dataclasses import dataclass

from app.llm import OllamaClient
from app.states.workflow import AgentRole, IntentType, RoutingDecision, TaskType


@dataclass(frozen=True)
class PlannerResult:
    decision: RoutingDecision | None
    raw_response: str


class LLMPlanner:
    def __init__(self, llm: OllamaClient | None = None) -> None:
        self.llm = llm or OllamaClient()

    def plan(self, input_text: str, memory_context: str = "") -> PlannerResult:
        system_prompt = (
            "You are a routing planner for a banking AI backend. Return only valid JSON. "
            "Do not answer the user. Select one intent, route, task_type, optional document_type, "
            "confidence from 0 to 1, and a short reason."
        )
        user_prompt = (
            "Allowed intents: customer_lookup, masking_request, banking_faq, owner_question, "
            "realtime_web, document_intelligence, research_report, credit_risk, smalltalk, unknown.\n"
            "Allowed routes: orchestrator, customer_data_guard, banking_knowledge.\n"
            "Allowed task_types: orchestrator_direct_response, customer_data_masking, "
            "customer_profile_review, document_intelligence, research_report, "
            "banking_process_support, credit_risk_support, general_banking_knowledge.\n"
            "Allowed document_type values: customer_profile, banking_faq, process, owner_profile, "
            "policy, public_reference, null.\n\n"
            f"Memory context:\n{memory_context or 'No memory context.'}\n\n"
            f"User request:\n{input_text}\n\n"
            "JSON shape:\n"
            '{"intent":"...","route":"...","task_type":"...","document_type":null,'
            '"confidence":0.0,"reason":"..."}'
        )
        raw_response = self.llm.generate(system_prompt, user_prompt)
        return PlannerResult(
            decision=self._parse_decision(raw_response),
            raw_response=raw_response,
        )

    def _parse_decision(self, raw_response: str) -> RoutingDecision | None:
        payload = extract_json_object(raw_response)
        if payload is None:
            return None
        try:
            intent = IntentType(payload.get("intent"))
            route = AgentRole(payload.get("route"))
            task_type = TaskType(payload.get("task_type"))
        except Exception:
            return None

        document_type = payload.get("document_type")
        if document_type == "":
            document_type = None
        confidence = payload.get("confidence", 0.0)
        try:
            confidence_value = max(0.0, min(float(confidence), 1.0))
        except (TypeError, ValueError):
            confidence_value = 0.0

        return RoutingDecision(
            intent=intent,
            route=route,
            task_type=task_type,
            document_type=document_type,
            confidence=confidence_value,
            routing_source="llm_planner",
            reason=str(payload.get("reason") or ""),
            llm_planner_output=raw_response,
        )


def extract_json_object(value: str) -> dict | None:
    stripped = value.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        candidate = stripped
    else:
        match = re.search(r"\{.*\}", value, flags=re.DOTALL)
        if not match:
            return None
        candidate = match.group(0)

    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None
