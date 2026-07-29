from app.agents.base import BaseAgent
from app.llm import OllamaClient
from app.states.workflow import AgentRole, TaskType
from app.tools import ToolRegistry, default_tool_registry


class OrchestratorAgent(BaseAgent):
    def __init__(
        self,
        llm: OllamaClient | None = None,
        tools: ToolRegistry | None = None,
    ) -> None:
        self.llm = llm or OllamaClient()
        self.tools = tools or default_tool_registry

    def route(self, input_text: str) -> str:
        task_type = self.classify_task(input_text)
        if task_type == TaskType.orchestrator_direct_response:
            return AgentRole.orchestrator.value
        if task_type in {
            TaskType.customer_data_masking,
            TaskType.customer_profile_review,
        }:
            return AgentRole.customer_data_guard.value
        return AgentRole.banking_knowledge.value

    def classify_task(self, input_text: str) -> TaskType:
        text = input_text.lower()

        if self._contains_any(
            text,
            [
                "mask",
                "an danh",
                "che thong tin",
                "cccd",
                "cmnd",
                "so dien thoai",
                "sdt",
                "phone",
                "pii",
            ],
        ):
            return TaskType.customer_data_masking

        if self._contains_any(
            text,
            [
                "ho so khach hang",
                "thong tin khach hang",
                "customer profile",
                "kyc",
                "kyb",
                "doi chieu khach hang",
            ],
        ):
            return TaskType.customer_profile_review

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
            return TaskType.document_intelligence

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
            return TaskType.research_report

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
            return TaskType.banking_process_support

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
            return TaskType.credit_risk_support

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
            return TaskType.general_banking_knowledge

        return TaskType.orchestrator_direct_response

    def build_plan(self, input_text: str) -> list[str]:
        task_type = self.classify_task(input_text)
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

    def summarize(self, input_text: str) -> str:
        route = self.route(input_text)
        task_type = self.classify_task(input_text)
        deterministic_summary = (
            f"Orchestrator classified task_type={task_type.value}, "
            f"route={route}, input_length={len(input_text)}."
        )
        if route == AgentRole.orchestrator.value:
            return deterministic_summary

        llm_summary = self._generate_orchestration_summary(
            input_text=input_text,
            route=route,
            task_type=task_type,
            workflow_plan=self.build_plan(input_text),
        )
        return f"{deterministic_summary} LLM rationale: {llm_summary}"

    def run(self, input_text: str, task_type: TaskType | None = None) -> str:
        return self.summarize(input_text)

    def answer_direct(self, input_text: str) -> str:
        task_type = self.classify_task(input_text)
        workflow_plan = self.build_plan(input_text)
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
                "bây giờ"
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
            "Explain why this route and plan are appropriate for staff workflow."
        )
        try:
            return self.llm.generate(system_prompt, user_prompt)
        except Exception as exc:
            return f"LLM unavailable; used deterministic orchestration only. Reason: {exc}"

    @staticmethod
    def _contains_any(text: str, keywords: list[str]) -> bool:
        return any(keyword in text for keyword in keywords)
