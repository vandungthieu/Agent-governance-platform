import re
import unicodedata

from app.agents.base import BaseAgent
from app.llm import OllamaClient
from app.routing import LLMPlanner, SemanticIntentRouter
from app.states.workflow import AgentRole, IntentType, RoutingDecision, TaskType
from app.tools import ToolRegistry, default_tool_registry


class OrchestratorAgent(BaseAgent):
    def __init__(
        self,
        llm: OllamaClient | None = None,
        tools: ToolRegistry | None = None,
        semantic_router: SemanticIntentRouter | None = None,
        llm_planner: LLMPlanner | None = None,
    ) -> None:
        self.llm = llm or OllamaClient()
        self.tools = tools or default_tool_registry
        self.semantic_router = semantic_router or SemanticIntentRouter()
        self.llm_planner = llm_planner or LLMPlanner(self.llm)

    def decide(self, input_text: str, memory_context: str = "") -> RoutingDecision:
        deterministic_decision = self._deterministic_decision(input_text)
        if deterministic_decision.intent != IntentType.unknown:
            return deterministic_decision

        semantic_result = self.semantic_router.route(input_text)
        if semantic_result is not None:
            return self._decision_from_intent(
                semantic_result.intent,
                confidence=semantic_result.confidence,
                routing_source=semantic_result.source,
                reason=f"matched_example={semantic_result.matched_example}",
            )

        try:
            planner_result = self.llm_planner.plan(input_text, memory_context=memory_context)
            if planner_result.decision is not None and planner_result.decision.confidence >= 0.55:
                return planner_result.decision
        except Exception:
            pass

        return self._keyword_fallback_decision(input_text)

    def route(self, input_text: str) -> str:
        return self.decide(input_text).route.value

    def classify_task(self, input_text: str) -> TaskType:
        return self.decide(input_text).task_type

    def _deterministic_decision(self, input_text: str) -> RoutingDecision:
        text = input_text.lower()

        if self._is_realtime_web_query(text):
            return self._decision_from_intent(
                IntentType.realtime_web,
                confidence=0.98,
                routing_source="rule",
                reason="Detected realtime/public information request.",
            )

        if self._looks_like_owner_question(text):
            return self._decision_from_intent(
                IntentType.owner_question,
                confidence=0.98,
                routing_source="rule",
                reason="Detected owner/project creator question.",
            )

        if self._contains_any(
            text,
            [
                "mask",
                "an danh",
                "che thong tin",
                "ma hoa",
                "bao mat thong tin",
                "bao ve thong tin",
                "redact",
                "redaction",
                "pii",
            ],
        ):
            return self._decision_from_intent(
                IntentType.masking_request,
                confidence=0.98,
                routing_source="rule",
                reason="Detected explicit masking/redaction request.",
            )

        if self._looks_like_customer_profile_lookup(text):
            return self._decision_from_intent(
                IntentType.customer_lookup,
                confidence=0.98,
                routing_source="rule",
                reason="Detected structured customer-profile lookup.",
            )

        return RoutingDecision(intent=IntentType.unknown, confidence=0.0, routing_source="rule")

    def _keyword_fallback_decision(self, input_text: str) -> RoutingDecision:
        text = input_text.lower()

        if self._contains_any(
            text,
            [
                "ho so khach hang",
                "thong tin khach hang",
                "khach hang",
                "khách hàng",
                "customer profile",
                "customer",
                "kyc",
                "kyb",
                "doi chieu khach hang",
            ],
        ):
            return self._decision_from_intent(
                IntentType.customer_lookup,
                confidence=0.62,
                routing_source="keyword_fallback",
                reason="Matched customer profile keywords.",
            )

        if self._contains_any(
            text,
            [
                "doc ho so",
                "doc tai lieu",
                "trich xuat",
                "tom tat tai lieu",
                "hop dong",
                "sao ke",
                "bao cao tai chinh",
                "document",
                "ocr",
            ],
        ):
            return self._decision_from_intent(
                IntentType.document_intelligence,
                confidence=0.62,
                routing_source="keyword_fallback",
                reason="Matched document intelligence keywords.",
            )

        if self._contains_any(
            text,
            [
                "bao cao nghien cuu",
                "research report",
                "memo",
                "to trinh",
                "nhan dinh thi truong",
                "phan tich nganh",
            ],
        ):
            return self._decision_from_intent(
                IntentType.research_report,
                confidence=0.62,
                routing_source="keyword_fallback",
                reason="Matched research/report keywords.",
            )

        if self._contains_any(
            text,
            [
                "quy trinh",
                "san pham",
                "lai suat",
                "bieu phi",
                "mo the",
                "mo tai khoan",
                "banking process",
            ],
        ):
            return self._decision_from_intent(
                IntentType.banking_faq,
                confidence=0.62,
                routing_source="keyword_fallback",
                reason="Matched banking process/FAQ keywords.",
            )

        if self._contains_any(
            text,
            [
                "tin dung",
                "khoan vay",
                "vay von",
                "rui ro",
                "tham dinh",
                "credit",
                "risk",
            ],
        ):
            return self._decision_from_intent(
                IntentType.credit_risk,
                confidence=0.62,
                routing_source="keyword_fallback",
                reason="Matched credit risk keywords.",
            )

        if self._contains_any(
            text,
            [
                "ngan hang",
                "bank",
                "banking",
                "tai chinh",
                "finance",
                "tien gui",
                "tiet kiem",
                "thanh toan",
                "chuyen khoan",
                "the",
                "card",
                "atm",
                "core banking",
                "crm",
                "los",
                "basel",
                "aml",
                "compliance",
            ],
        ):
            return self._decision_from_intent(
                IntentType.banking_faq,
                confidence=0.58,
                routing_source="keyword_fallback",
                reason="Matched general banking keywords.",
            )

        return self._decision_from_intent(
            IntentType.smalltalk,
            confidence=0.45,
            routing_source="keyword_fallback",
            reason="No specialist intent matched.",
        )

    def _decision_from_intent(
        self,
        intent: IntentType,
        confidence: float,
        routing_source: str,
        reason: str = "",
    ) -> RoutingDecision:
        mapping: dict[IntentType, tuple[AgentRole, TaskType, str | None]] = {
            IntentType.customer_lookup: (
                AgentRole.customer_data_guard,
                TaskType.customer_profile_review,
                "customer_profile",
            ),
            IntentType.masking_request: (
                AgentRole.customer_data_guard,
                TaskType.customer_data_masking,
                "customer_profile",
            ),
            IntentType.banking_faq: (
                AgentRole.banking_knowledge,
                TaskType.banking_process_support,
                "banking_faq",
            ),
            IntentType.owner_question: (
                AgentRole.banking_knowledge,
                TaskType.general_banking_knowledge,
                "owner_profile",
            ),
            IntentType.realtime_web: (
                AgentRole.orchestrator,
                TaskType.orchestrator_direct_response,
                None,
            ),
            IntentType.document_intelligence: (
                AgentRole.banking_knowledge,
                TaskType.document_intelligence,
                "policy",
            ),
            IntentType.research_report: (
                AgentRole.banking_knowledge,
                TaskType.research_report,
                "public_reference",
            ),
            IntentType.credit_risk: (
                AgentRole.banking_knowledge,
                TaskType.credit_risk_support,
                "policy",
            ),
            IntentType.smalltalk: (
                AgentRole.orchestrator,
                TaskType.orchestrator_direct_response,
                None,
            ),
            IntentType.unknown: (
                AgentRole.orchestrator,
                TaskType.orchestrator_direct_response,
                None,
            ),
        }
        route, task_type, document_type = mapping[intent]
        return RoutingDecision(
            intent=intent,
            route=route,
            task_type=task_type,
            document_type=document_type,
            confidence=confidence,
            routing_source=routing_source,
            reason=reason,
        )

    def _is_realtime_web_query(self, text: str) -> bool:
        realtime_terms = [
            "thoi tiet",
            "thời tiết",
            "nhiet do",
            "nhiệt độ",
            "du bao",
            "dự báo",
            "hom nay",
            "hôm nay",
            "hien tai",
            "hiện tại",
            "hien nay",
            "hiện nay",
            "moi nhat",
            "mới nhất",
            "tin moi",
            "tin mới",
            "cap nhat",
            "cập nhật",
            "gia vang",
            "giá vàng",
            "ty gia",
            "tỷ giá",
        ]
        return self._contains_any(text, realtime_terms)

    def _looks_like_owner_question(self, text: str) -> bool:
        owner_terms = [
            "ai tao ra ban",
            "ai tao ra he thong",
            "ai tao ra du an",
            "ai tao nen ban",
            "ai tao nen he thong",
            "ai tao nen du an",
            "nguoi tao ra ban",
            "nguoi tao ra he thong",
            "nguoi tao ra du an",
            "nguoi phat trien ban",
            "nguoi phat trien he thong",
            "nguoi phat trien du an",
            "tac gia",
            "author",
            "owner",
            "creator",
            "developer cua ban",
            "developer cua he thong",
            "developer cua du an",
            "du an nay cua ai",
            "he thong nay cua ai",
            "ban duoc tao boi ai",
            "he thong duoc tao boi ai",
        ]
        return self._contains_any(text, owner_terms)

    def _looks_like_customer_profile_lookup(self, text: str) -> bool:
        has_customer_reference = self._contains_any(
            text,
            [
                "khach hang",
                "khách hàng",
                "customer",
                "anh ta",
                "ong ay",
                "ông ấy",
                "ong ta",
                "ông ta",
                "chi ay",
                "chị ấy",
                "co ay",
                "cô ấy",
                "nguoi do",
                "người đó",
                "nguoi nay",
                "người này",
            ],
        )
        has_profile_field = self._contains_any(
            text,
            [
                "cccd",
                "cmnd",
                "so dien thoai",
                "sdt",
                "phone",
                "dien thoai",
                "email",
                "dia chi",
                "address",
                "so tai khoan",
                "ngay sinh",
                "nam sinh",
                "sinh nam",
                "nghe nghiep",
                "trang thai",
                "phan hang",
                "thong tin",
                "ho so",
            ],
        )
        return has_customer_reference and has_profile_field

    def build_plan(self, input_text: str) -> list[str]:
        task_type = self.classify_task(input_text)
        return self.build_plan_for_task(task_type)

    def build_plan_for_task(self, task_type: TaskType) -> list[str]:
        plans = {
            TaskType.orchestrator_direct_response: [
                "Recognize that the request is outside specialist agent boundaries.",
                "Handle the request directly at orchestration level.",
                "Return a concise response or ask for clarification when needed.",
            ],
            TaskType.customer_data_masking: [
                "Detect customer identifiers and sensitive fields.",
                "Mask or normalize customer data before downstream use.",
                "Return sanitized content for staff review.",
            ],
            TaskType.customer_profile_review: [
                "Identify customer profile fields in the request.",
                "Check whether key KYC/KYB information appears complete.",
                "Return a structured customer data review.",
            ],
            TaskType.document_intelligence: [
                "Identify document type and requested extraction goal.",
                "Extract or summarize key banking information.",
                "Highlight missing fields, inconsistencies, and next actions.",
            ],
            TaskType.research_report: [
                "Identify report scope, audience, and required sections.",
                "Draft a research report structure with key findings.",
                "Return a staff-ready draft for human review.",
            ],
            TaskType.banking_process_support: [
                "Identify the banking process or product being requested.",
                "Map the request to internal process guidance.",
                "Return steps, required documents, and operational notes.",
            ],
            TaskType.credit_risk_support: [
                "Identify credit context and risk review objective.",
                "Summarize risk factors and missing evidence.",
                "Return a preliminary credit support checklist.",
            ],
            TaskType.general_banking_knowledge: [
                "Identify the banking knowledge question.",
                "Prepare a concise answer grounded in internal knowledge.",
                "Flag uncertainty when source data is missing.",
            ],
        }
        return plans[task_type]

    def summarize(
        self,
        input_text: str,
        memory_context: str = "",
        decision: RoutingDecision | None = None,
    ) -> str:
        decision = decision or self.decide(input_text, memory_context=memory_context)
        route = decision.route.value
        task_type = decision.task_type
        deterministic_summary = (
            f"Orchestrator classified task_type={task_type.value}, "
            f"route={route}, intent={decision.intent.value}, "
            f"confidence={decision.confidence:.2f}, source={decision.routing_source}, "
            f"input_length={len(input_text)}."
        )
        if route != AgentRole.orchestrator.value:
            return deterministic_summary

        llm_summary = self._generate_orchestration_summary(
            input_text=input_text,
            route=route,
            task_type=task_type,
            workflow_plan=self.build_plan_for_task(task_type),
            memory_context=memory_context,
        )
        return f"{deterministic_summary} LLM rationale: {llm_summary}"

    def run(
        self,
        input_text: str,
        task_type: TaskType | None = None,
        memory_context: str = "",
        decision: RoutingDecision | None = None,
    ) -> str:
        return self.summarize(input_text, memory_context=memory_context, decision=decision)

    def answer_direct(self, input_text: str, memory_context: str = "") -> str:
        task_type = self.classify_task(input_text)
        workflow_plan = self.build_plan_for_task(task_type)
        web_results = self._search_web_if_needed(input_text)
        system_prompt = (
            "You are OrchestratorAgent for an internal finance and banking assistant. "
            "Handle requests that are outside specialist agent boundaries. "
            "Answer in concise Vietnamese. For greetings or identity questions, introduce "
            "yourself naturally as the orchestrator for the internal banking assistant. "
            "If the request is unrelated to the assistant scope, politely redirect the user "
            "toward banking, customer-data, document, report, or workflow tasks. "
            "Use web_search_results only when they are non-empty and relevant. Clearly state "
            "when information comes from public web context."
        )
        user_prompt = (
            f"User request:\n{input_text}\n\n"
            f"Task type: {task_type.value}\n"
            f"Workflow plan: {workflow_plan}\n\n"
            f"Memory context:\n{memory_context or 'No memory context available.'}\n\n"
            f"web_search_results:\n{web_results}\n\n"
            "Provide only the final user-facing answer."
        )
        try:
            return self.llm.generate(system_prompt, user_prompt)
        except Exception as exc:
            return f"Toi la OrchestratorAgent. LLM hien khong kha dung: {exc}"

    def _search_web_if_needed(self, input_text: str) -> list[dict]:
        if not self._should_search_web(input_text):
            return []

        result = self.tools.run("web.search", query=input_text, limit=3)
        return result.output

    def _should_search_web(self, input_text: str) -> bool:
        text = input_text.lower()
        return self._contains_any(
            text,
            [
                "thoi tiet",
                "thời tiết",
                "nhiet do",
                "nhiệt độ",
                "du bao",
                "dự báo",
                "moi nhat",
                "mới nhất",
                "hien nay",
                "hiện nay",
                "tin moi",
                "tin mới",
                "cap nhat",
                "cập nhật",
                "internet",
                "hiện tại",
                "hôm nay",
                "hom nay",
                "hien tai",
                "bây giờ",
                "web",
                "public",
                "cong khai",
                "công khai",
                "thi truong",
                "thị trường",
                "xu huong",
                "xu hướng",
            ],
        )

    def _generate_orchestration_summary(
        self,
        input_text: str,
        route: str,
        task_type: TaskType,
        workflow_plan: list[str],
        memory_context: str = "",
    ) -> str:
        if route == AgentRole.orchestrator.value:
            system_prompt = (
                "You are OrchestratorAgent for an internal finance and banking assistant. "
                "The request is outside the two specialist agent boundaries. "
                "Handle it directly in concise Vietnamese. If it is unrelated to the "
                "banking assistant scope, politely say so and ask the user to restate "
                "a banking, customer-data, document, report, or workflow task."
            )
            user_prompt = (
                f"User request:\n{input_text}\n\n"
                f"Task type: {task_type.value}\n"
                f"Workflow plan: {workflow_plan}\n\n"
                f"Memory context:\n{memory_context or 'No memory context available.'}\n\n"
                "Provide the direct orchestrator response."
            )
            try:
                return self.llm.generate(system_prompt, user_prompt)
            except Exception as exc:
                return f"LLM unavailable; used deterministic orchestration only. Reason: {exc}"

        system_prompt = (
            "You are OrchestratorAgent for an internal finance and banking assistant. "
            "Your job is to explain routing, task classification, and workflow plan. "
            "Do not solve the specialist task. Answer in concise Vietnamese."
        )
        user_prompt = (
            f"User request:\n{input_text}\n\n"
            f"Selected route: {route}\n"
            f"Task type: {task_type.value}\n"
            f"Workflow plan: {workflow_plan}\n\n"
            f"Memory context:\n{memory_context or 'No memory context available.'}\n\n"
            "Explain why this route and plan are appropriate for staff workflow."
        )
        try:
            return self.llm.generate(system_prompt, user_prompt)
        except Exception as exc:
            return f"LLM unavailable; used deterministic orchestration only. Reason: {exc}"

    @staticmethod
    def _contains_any(text: str, keywords: list[str]) -> bool:
        normalized_text = OrchestratorAgent._normalize_text(text)
        return any(OrchestratorAgent._normalize_text(keyword) in normalized_text for keyword in keywords)

    @staticmethod
    def _normalize_text(value: str) -> str:
        value = value.replace("Đ", "D").replace("đ", "d")
        without_accents = "".join(
            character
            for character in unicodedata.normalize("NFD", value.lower())
            if unicodedata.category(character) != "Mn"
        )
        return re.sub(r"[^a-z0-9]+", " ", without_accents)
