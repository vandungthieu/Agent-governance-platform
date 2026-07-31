import re
import unicodedata

from app.agents.base import BaseAgent
from app.db.knowledge_repository import list_knowledge_chunks
from app.db.session import SessionLocal
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

    def run(
        self,
        input_text: str,
        task_type: TaskType | None = None,
        memory_context: str = "",
    ) -> str:
        task_type = task_type or TaskType.customer_data_masking

        if task_type == TaskType.customer_profile_review:
            direct_answer = self._answer_customer_profile_lookup(
                input_text=input_text,
                retrieved_knowledge=self._retrieve_customer_profile_fast(input_text),
            )
            if direct_answer:
                return direct_answer

            masking_result = self.tools.run("customer_data.mask", text=input_text)
            checklist_result = self.tools.run("customer_profile.checklist", text=input_text)
            knowledge_result = self.tools.run(
                "knowledge.search",
                query=input_text,
                limit=5,
            )
            direct_answer = self._answer_customer_profile_lookup(
                input_text=input_text,
                retrieved_knowledge=knowledge_result.output,
            )
            if direct_answer:
                return direct_answer
            return self._generate_customer_profile_review(
                input_text=input_text,
                memory_context=memory_context,
                masked_text=masking_result.output,
                checklist=checklist_result.output,
                retrieved_knowledge=knowledge_result.output,
            )

        masking_result = self.tools.run("customer_data.mask", text=input_text)
        knowledge_result = self.tools.run(
            "knowledge.search",
            query="PII masking customer data privacy",
            limit=3,
        )
        return self._generate_masking_review(
            masking_result.output,
            masking_result.metadata,
            knowledge_result.output,
            memory_context=memory_context,
        )

    def _retrieve_customer_profile_fast(self, input_text: str) -> list[dict]:
        customer_name = self._extract_customer_name_from_input(input_text)
        if not customer_name:
            return []
        with SessionLocal() as db:
            chunks = list_knowledge_chunks(
                db=db,
                limit=100,
                document_type="customer_profile",
            )
        normalized_name = self._normalize_text(customer_name)
        full_content = "\n".join(
            str(chunk.get("content") or "")
            for chunk in sorted(chunks, key=lambda chunk: chunk.get("chunk_index", 0))
        )
        customer_section = self._extract_customer_section(full_content, normalized_name)
        if not customer_section:
            return []
        return [
            {
                "title": "customer_profile_fast_lookup",
                "document_type": "customer_profile",
                "chunk_index": 0,
                "content": customer_section,
                "rank": 1.0,
            }
        ]

    def _extract_customer_section(self, content: str, normalized_name: str) -> str | None:
        sections = re.split(r"(?=^##\s+Customer\s+)", content, flags=re.MULTILINE)
        for section in sections:
            if normalized_name in self._normalize_text(section):
                return section
        return None

    def _generate_customer_profile_review(
        self,
        input_text: str,
        memory_context: str,
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
            f"Memory context:\n{memory_context or 'No memory context available.'}\n\n"
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
        memory_context: str = "",
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
            f"Memory context:\n{memory_context or 'No memory context available.'}\n\n"
            f"Detection metadata:\n{metadata}\n\n"
            f"Retrieved internal knowledge:\n{retrieved_knowledge}\n\n"
            "Write a concise Vietnamese review."
        )
        return self._safe_generate(system_prompt, user_prompt)

    def _answer_customer_profile_lookup(
        self,
        input_text: str,
        retrieved_knowledge: list[dict],
    ) -> str | None:
        requested_field = self._requested_customer_field(input_text)
        if not requested_field:
            return None

        combined_content = "\n".join(
            str(item.get("content") or "") for item in retrieved_knowledge[:3]
        )
        field_value = self._extract_markdown_table_value(combined_content, requested_field)
        if not field_value:
            return None

        customer_name = self._extract_customer_name(input_text, combined_content)
        if requested_field == "Ngày sinh" and self._contains_any(input_text, ["sinh nam", "nam sinh"]):
            year_match = re.search(r"\b(\d{4})\b", field_value)
            if year_match:
                return f"Khách hàng {customer_name} sinh năm {year_match.group(1)}."

        return f"{requested_field} của khách hàng {customer_name} là {field_value}."

    def _requested_customer_field(self, input_text: str) -> str | None:
        field_keywords = [
            ("Điện thoại", ["so dien thoai", "sdt", "phone", "dien thoai"]),
            ("Email", ["email", "mail"]),
            ("Địa chỉ", ["dia chi", "address"]),
            ("Số tài khoản", ["so tai khoan", "account number"]),
            ("Ngày sinh", ["ngay sinh", "sinh nam", "nam sinh", "birth"]),
            ("Trạng thái", ["trang thai", "status"]),
            ("Phân hạng", ["phan hang", "segment", "vip"]),
        ]
        for field_label, keywords in field_keywords:
            if self._contains_any(input_text, keywords):
                return field_label
        return None

    @staticmethod
    def _extract_markdown_table_value(content: str, field_label: str) -> str | None:
        pattern = rf"\|\s*{re.escape(field_label)}\s*\|\s*([^|]+?)\s*\|"
        match = re.search(pattern, content, flags=re.IGNORECASE)
        return match.group(1).strip() if match else None

    def _extract_customer_name(self, input_text: str, content: str) -> str:
        names = re.findall(r"\|\s*Họ và tên\s*\|\s*([^|]+?)\s*\|", content, flags=re.IGNORECASE)
        normalized_input = self._normalize_text(input_text)
        for name in names:
            if self._normalize_text(name) in normalized_input:
                return name.strip()
        input_name = self._extract_customer_name_from_input(input_text)
        if input_name:
            return input_name
        return names[0].strip() if names else "được hỏi"

    @staticmethod
    def _extract_customer_name_from_input(input_text: str) -> str | None:
        match = re.search(
            r"(?:khách hàng|khach hang|customer)\s+(.+?)(?:\s+(?:là|la|có|co|sinh|số|so|email|địa|dia)\b|$)",
            input_text.strip(),
            flags=re.IGNORECASE,
        )
        if not match:
            return None
        name = match.group(1).strip(" ?.!")
        return name or None

    def _contains_any(self, text: str, keywords: list[str]) -> bool:
        normalized_text = self._normalize_text(text)
        return any(self._normalize_text(keyword) in normalized_text for keyword in keywords)

    @staticmethod
    def _normalize_text(value: str) -> str:
        value = value.replace("Đ", "D").replace("đ", "d")
        without_accents = "".join(
            character
            for character in unicodedata.normalize("NFD", value.lower())
            if unicodedata.category(character) != "Mn"
        )
        return re.sub(r"[^a-z0-9]+", " ", without_accents).strip()

    def _safe_generate(self, system_prompt: str, user_prompt: str) -> str:
        try:
            return self.llm.generate(system_prompt, user_prompt)
        except Exception as exc:
            return (
                "Đã xử lý dữ liệu khách hàng bằng công cụ nội bộ, "
                "nhưng hiện chưa gọi được mô hình ngôn ngữ local để tạo nhận xét. "
                f"Lý do kỹ thuật: {exc}"
            )
