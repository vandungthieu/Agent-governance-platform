from app.agents.base import BaseAgent
from app.llm import OllamaClient
from app.states.workflow import TaskType
from app.tools import ToolRegistry, default_tool_registry


class CustomerDataGuardAgent(BaseAgent):
    def __init__(
        self,
        tools: ToolRegistry | None = None,
        llm: OllamaClient | None = None,
    ) -> None:
        self.tools = tools or default_tool_registry
        self.llm = llm or OllamaClient()

    def run(self, input_text: str, task_type: TaskType | None = None) -> str:
        task_type = task_type or TaskType.customer_data_masking
        masking_result = self.tools.run("customer_data.mask", text=input_text)

        if task_type == TaskType.customer_profile_review:
            checklist_result = self.tools.run("customer_profile.checklist", text=input_text)
            knowledge_result = self.tools.run(
                "knowledge.search",
                query=input_text,
                limit=5,
            )
            return self._generate_customer_profile_review(
                input_text=input_text,
                masked_text=masking_result.output,
                checklist=checklist_result.output,
                retrieved_knowledge=knowledge_result.output,
            )

        knowledge_result = self.tools.run(
            "knowledge.search",
            query="PII masking customer data privacy",
            limit=3,
        )
        return self._generate_masking_review(
            masking_result.output,
            masking_result.metadata,
            knowledge_result.output,
        )

    def _generate_customer_profile_review(
        self,
        input_text: str,
        masked_text: str,
        checklist: dict,
        retrieved_knowledge: list[dict],
    ) -> str:
        system_prompt = (
            "You are CustomerDataGuardAgent for an internal banking assistant. "
            "Authentication and staff authorization are handled by an upstream auth service, so do not "
            "perform role checks or refuse ordinary customer-profile fields in this agent. Use retrieved "
            "internal knowledge when available and answer the user's exact customer-profile question first "
            "when the answer is present. Do not reveal OTP, PIN, CVV, passwords, tokens, or secrets. If a "
            "requested value is not present in retrieved knowledge, say it is not found in internal data. "
            "Return concise Vietnamese output."
        )
        user_prompt = (
            f"User request:\n{input_text}\n\n"
            f"Masked customer text:\n{masked_text}\n\n"
            f"Checklist result:\n{checklist}\n\n"
            f"Retrieved internal knowledge:\n{retrieved_knowledge}\n\n"
            "Create a short staff-facing review."
        )
        return self._safe_generate(system_prompt, user_prompt)

    def _generate_masking_review(
        self,
        masked_text: str,
        metadata: dict,
        retrieved_knowledge: list[dict],
    ) -> str:
        system_prompt = (
            "You are CustomerDataGuardAgent for an internal banking assistant. "
            "Summarize what customer data was detected after masking. Authentication and staff "
            "authorization are handled by an upstream auth service, so do not perform role checks here. "
            "Do not reveal OTP, PIN, CVV, passwords, tokens, or secrets. Use retrieved internal knowledge "
            "when available."
        )
        user_prompt = (
            f"Masked text:\n{masked_text}\n\n"
            f"Detection metadata:\n{metadata}\n\n"
            f"Retrieved internal knowledge:\n{retrieved_knowledge}\n\n"
            "Write a concise Vietnamese review."
        )
        return self._safe_generate(system_prompt, user_prompt)

    def _safe_generate(self, system_prompt: str, user_prompt: str) -> str:
        try:
            return self.llm.generate(system_prompt, user_prompt)
        except Exception as exc:
            return (
                "Đã xử lý dữ liệu khách hàng bằng công cụ nội bộ, "
                "nhưng hiện chưa gọi được mô hình ngôn ngữ local để tạo nhận xét. "
                f"Lý do kỹ thuật: {exc}"
            )
