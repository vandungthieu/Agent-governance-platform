import re
import unicodedata

from app.agents.base import BaseAgent
from app.db.knowledge_repository import list_knowledge_chunks
from app.db.session import SessionLocal
from app.llm import OllamaClient
from app.states.workflow import IntentType, TaskType
from app.tools import ToolRegistry, default_tool_registry


class BankingKnowledgeAgent(BaseAgent):
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
        intent: IntentType | None = None,
        document_type: str | None = None,
    ) -> str:
        task_type = task_type or TaskType.general_banking_knowledge

        handlers = {
            TaskType.document_intelligence: self._handle_document_intelligence,
            TaskType.research_report: self._handle_research_report,
            TaskType.banking_process_support: self._handle_banking_process_support,
            TaskType.credit_risk_support: self._handle_credit_risk_support,
            TaskType.general_banking_knowledge: self._handle_general_banking_knowledge,
        }
        handler = handlers.get(task_type, self._handle_general_banking_knowledge)
        return handler(input_text, memory_context, intent=intent, document_type=document_type)

    def _handle_document_intelligence(
        self,
        input_text: str,
        memory_context: str = "",
        intent: IntentType | None = None,
        document_type: str | None = None,
    ) -> str:
        extraction = self.tools.run("document.extract", text=input_text)
        knowledge = self._retrieve_knowledge(input_text, document_type=document_type)
        return self._generate(
            task="Document Intelligence",
            input_text=input_text,
            memory_context=memory_context,
            tool_context={
                "document_extraction": extraction.output,
                "retrieved_knowledge": knowledge,
            },
        )

    def _handle_research_report(
        self,
        input_text: str,
        memory_context: str = "",
        intent: IntentType | None = None,
        document_type: str | None = None,
    ) -> str:
        template = self.tools.run("research_report.template", topic=input_text)
        knowledge = self._retrieve_knowledge(input_text, document_type=document_type)
        web_results = self._search_web(input_text)
        return self._generate(
            task="Research Report Drafting",
            input_text=input_text,
            memory_context=memory_context,
            tool_context={
                "report_template": template.output,
                "retrieved_knowledge": knowledge,
                "web_search_results": web_results,
            },
        )

    def _handle_banking_process_support(
        self,
        input_text: str,
        memory_context: str = "",
        intent: IntentType | None = None,
        document_type: str | None = None,
    ) -> str:
        checklist = self.tools.run("banking_process.checklist", text=input_text)
        direct_answer = self._answer_from_retrieved_faq(
            input_text,
            self._retrieve_banking_knowledge_fast(input_text, document_type=document_type),
        )
        if direct_answer:
            return direct_answer
        knowledge = self._retrieve_knowledge(input_text, limit=3, document_type=document_type)
        direct_answer = self._answer_from_retrieved_faq(input_text, knowledge)
        if direct_answer:
            return direct_answer
        return self._generate(
            task="Banking Process Support",
            input_text=input_text,
            memory_context=memory_context,
            tool_context={
                "process_checklist": checklist.output,
                "retrieved_knowledge": knowledge,
            },
        )

    def _handle_credit_risk_support(
        self,
        input_text: str,
        memory_context: str = "",
        intent: IntentType | None = None,
        document_type: str | None = None,
    ) -> str:
        checklist = self.tools.run("banking_process.checklist", text=input_text)
        knowledge = self._retrieve_knowledge(input_text, document_type=document_type)
        return self._generate(
            task="Credit Risk Support",
            input_text=input_text,
            memory_context=memory_context,
            tool_context={
                "credit_checklist": checklist.output,
                "retrieved_knowledge": knowledge,
            },
        )

    def _handle_general_banking_knowledge(
        self,
        input_text: str,
        memory_context: str = "",
        intent: IntentType | None = None,
        document_type: str | None = None,
    ) -> str:
        if intent == IntentType.owner_question or self._looks_like_owner_question(input_text):
            owner_knowledge = self._retrieve_owner_knowledge_fast(document_type=document_type)
            direct_answer = self._answer_owner_question(owner_knowledge)
            if direct_answer:
                return direct_answer
            return self._generate(
                task="Owner Knowledge",
                input_text=input_text,
                memory_context=memory_context,
                tool_context={"retrieved_knowledge": owner_knowledge},
            )

        direct_answer = self._answer_from_retrieved_faq(
            input_text,
            self._retrieve_banking_knowledge_fast(input_text, document_type=document_type),
        )
        if direct_answer:
            return direct_answer
        knowledge = self._retrieve_knowledge(input_text, limit=3, document_type=document_type)
        direct_answer = self._answer_from_retrieved_faq(input_text, knowledge)
        if direct_answer:
            return direct_answer
        return self._generate(
            task="General Banking Knowledge",
            input_text=input_text,
            memory_context=memory_context,
            tool_context={"retrieved_knowledge": knowledge},
        )

    def _retrieve_knowledge(
        self,
        input_text: str,
        limit: int = 5,
        document_type: str | None = None,
    ) -> list[dict]:
        result = self.tools.run("knowledge.search", query=input_text, limit=limit, document_type=document_type)
        return result.output

    def _search_web(self, input_text: str) -> list[dict]:
        result = self.tools.run("web.search", query=input_text, limit=3)
        return result.output

    def _retrieve_banking_knowledge_fast(
        self,
        input_text: str,
        document_type: str | None = None,
    ) -> list[dict]:
        query_tokens = self._tokens(input_text)
        if not query_tokens:
            return []
        with SessionLocal() as db:
            chunks = list_knowledge_chunks(db=db, limit=100, document_type=document_type or "public_reference")
        scored_chunks = []
        for chunk in chunks:
            content_tokens = self._tokens(str(chunk.get("content") or ""))
            overlap_score = len(query_tokens & content_tokens) / max(len(query_tokens), 1)
            if overlap_score <= 0:
                continue
            chunk["lexical_score"] = overlap_score
            scored_chunks.append(chunk)
        return sorted(scored_chunks, key=lambda chunk: chunk["lexical_score"], reverse=True)[:5]

    def _retrieve_owner_knowledge_fast(self, document_type: str | None = None) -> list[dict]:
        with SessionLocal() as db:
            chunks = list_knowledge_chunks(db=db, limit=200, document_type=document_type or "owner_profile")
            if not chunks and document_type:
                chunks = list_knowledge_chunks(db=db, limit=200, document_type="public_reference")

        owner_chunks = []
        for chunk in chunks:
            searchable_text = " ".join(
                str(chunk.get(key) or "")
                for key in ("title", "source_uri", "content")
            )
            normalized_text = self._normalize_text(searchable_text)
            if self._contains_owner_marker(normalized_text):
                chunk["lexical_score"] = 1.0
                owner_chunks.append(chunk)

        return owner_chunks[:5]

    def _generate(
        self,
        task: str,
        input_text: str,
        tool_context: object,
        memory_context: str = "",
    ) -> str:
        system_prompt = (
            "You are BankingKnowledgeAgent for an internal finance and banking assistant. "
            "Help employees with document intelligence, research drafts, banking processes, "
            "and credit support. Answer in Vietnamese. Be concise, structured, and careful. "
            "Use retrieved internal knowledge when available. Prioritize the highest-ranked "
            "retrieved chunks and answer the user's exact question first. Do not return a "
            "general process overview unless the user asked for the process. If retrieved knowledge is empty "
            "or insufficient, state that internal sources are missing and avoid inventing "
            "specific policies, numbers, or citations. Use web_search_results only as external "
            "context, and clearly separate it from internal knowledge."
        )
        user_prompt = (
            f"Task: {task}\n\n"
            f"User request:\n{input_text}\n\n"
            f"Memory context:\n{memory_context or 'No memory context available.'}\n\n"
            f"Tool context:\n{tool_context}\n\n"
            "Produce only the final staff-facing answer. Mention source titles when they appear "
            "in retrieved_knowledge or web_search_results."
        )
        try:
            return self.llm.generate(system_prompt, user_prompt)
        except Exception as exc:
            return (
                "Hiện chưa gọi được mô hình ngôn ngữ local. "
                f"Tác vụ đã được phân loại là {task}, nhưng cần thử lại sau. "
                f"Lý do kỹ thuật: {exc}"
            )

    def _answer_from_retrieved_faq(self, input_text: str, retrieved_knowledge: list[dict]) -> str | None:
        query_tokens = self._tokens(input_text)
        if not query_tokens:
            return None

        for item in retrieved_knowledge[:2]:
            content = str(item.get("content") or "")
            for heading, body in self._iter_markdown_sections(content):
                heading_tokens = self._tokens(heading)
                if not heading_tokens:
                    continue
                overlap_ratio = len(query_tokens & heading_tokens) / max(len(query_tokens), 1)
                if overlap_ratio < 0.45 and not heading_tokens.issubset(query_tokens | {"bao", "lau", "the"}):
                    continue

                answer = self._first_answer_paragraph(body)
                if answer:
                    source_title = item.get("title")
                    source_suffix = f"\n\nNguồn: {source_title}." if source_title else ""
                    return f"{answer}{source_suffix}"

        return None

    def _answer_owner_question(self, retrieved_knowledge: list[dict]) -> str | None:
        if not retrieved_knowledge:
            return None

        content = str(retrieved_knowledge[0].get("content") or "").strip()
        if not content:
            return None

        lines = [
            line.strip()
            for line in content.splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        if not lines:
            return None

        answer_lines = []
        for line in lines[:12]:
            cleaned = re.sub(r"^\*\s+", "- ", line)
            answer_lines.append(cleaned)

        source_title = retrieved_knowledge[0].get("title")
        source_suffix = f"\n\nNguồn: {source_title}." if source_title else ""
        return "\n".join(answer_lines).strip() + source_suffix

    def _looks_like_owner_question(self, input_text: str) -> bool:
        normalized_text = self._normalize_text(input_text)
        owner_question_terms = [
            "ai tao ra ban",
            "ai tao ra he thong",
            "ai tao ra du an",
            "nguoi tao ra ban",
            "nguoi tao ra he thong",
            "nguoi tao ra du an",
            "tac gia",
            "author",
            "owner",
            "creator",
            "founder",
            "developer cua ban",
            "developer cua he thong",
            "developer cua du an",
            "du an nay cua ai",
            "he thong nay cua ai",
            "ban duoc tao boi ai",
            "he thong duoc tao boi ai",
        ]
        return any(term in normalized_text for term in owner_question_terms)

    @staticmethod
    def _contains_owner_marker(normalized_text: str) -> bool:
        owner_markers = [
            "owner profile",
            "owner",
            "founder",
            "creator",
            "nguoi sang lap",
            "nha sang lap",
            "tac gia",
            "nguoi tao",
        ]
        return any(marker in normalized_text for marker in owner_markers)

    @staticmethod
    def _iter_markdown_sections(content: str) -> list[tuple[str, str]]:
        matches = list(re.finditer(r"^#{2,3}\s+(.+?)\s*$", content, flags=re.MULTILINE))
        sections: list[tuple[str, str]] = []
        for index, match in enumerate(matches):
            start = match.end()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(content)
            sections.append((match.group(1).strip(), content[start:end].strip()))
        return sections

    @staticmethod
    def _first_answer_paragraph(body: str) -> str | None:
        paragraphs = [
            paragraph.strip()
            for paragraph in re.split(r"\n\s*\n|^---$", body, flags=re.MULTILINE)
            if paragraph.strip()
        ]
        for paragraph in paragraphs:
            if paragraph.startswith("|") or paragraph.startswith("#"):
                continue
            cleaned = re.sub(r"\s+", " ", paragraph.replace("- ", "")).strip()
            if cleaned:
                return cleaned
        return None

    def _tokens(self, value: str) -> set[str]:
        return {
            token
            for token in self._normalize_text(value).split()
            if len(token) >= 2 and token not in {"cua", "toi", "duoc", "khong", "la", "gi"}
        }

    @staticmethod
    def _normalize_text(value: str) -> str:
        value = value.replace("Đ", "D").replace("đ", "d")
        without_accents = "".join(
            character
            for character in unicodedata.normalize("NFD", value.lower())
            if unicodedata.category(character) != "Mn"
        )
        return re.sub(r"[^a-z0-9]+", " ", without_accents).strip()
