from app.agents.base import BaseAgent
from app.llm import OllamaClient
from app.states.workflow import TaskType
from app.tools import ToolRegistry, default_tool_registry


class BankingKnowledgeAgent(BaseAgent):
    def __init__(
        self,
        tools: ToolRegistry | None = None,
        llm: OllamaClient | None = None,
    ) -> None:
        self.tools = tools or default_tool_registry
        self.llm = llm or OllamaClient()

    def run(self, input_text: str, task_type: TaskType | None = None) -> str:
        task_type = task_type or TaskType.general_banking_knowledge

        handlers = {
            TaskType.document_intelligence: self._handle_document_intelligence,
            TaskType.research_report: self._handle_research_report,
            TaskType.banking_process_support: self._handle_banking_process_support,
            TaskType.credit_risk_support: self._handle_credit_risk_support,
            TaskType.general_banking_knowledge: self._handle_general_banking_knowledge,
        }
        handler = handlers.get(task_type, self._handle_general_banking_knowledge)
        return handler(input_text)

    def _handle_document_intelligence(self, input_text: str) -> str:
        extraction = self.tools.run("document.extract", text=input_text)
        knowledge = self._retrieve_knowledge(input_text)
        return self._generate(
            task="Document Intelligence",
            input_text=input_text,
            tool_context={
                "document_extraction": extraction.output,
                "retrieved_knowledge": knowledge,
            },
        )

    def _handle_research_report(self, input_text: str) -> str:
        template = self.tools.run("research_report.template", topic=input_text)
        knowledge = self._retrieve_knowledge(input_text)
        web_results = self._search_web(input_text)
        return self._generate(
            task="Research Report Drafting",
            input_text=input_text,
            tool_context={
                "report_template": template.output,
                "retrieved_knowledge": knowledge,
                "web_search_results": web_results,
            },
        )

    def _handle_banking_process_support(self, input_text: str) -> str:
        checklist = self.tools.run("banking_process.checklist", text=input_text)
        knowledge = self._retrieve_knowledge(input_text)
        return self._generate(
            task="Banking Process Support",
            input_text=input_text,
            tool_context={
                "process_checklist": checklist.output,
                "retrieved_knowledge": knowledge,
            },
        )

    def _handle_credit_risk_support(self, input_text: str) -> str:
        checklist = self.tools.run("banking_process.checklist", text=input_text)
        knowledge = self._retrieve_knowledge(input_text)
        return self._generate(
            task="Credit Risk Support",
            input_text=input_text,
            tool_context={
                "credit_checklist": checklist.output,
                "retrieved_knowledge": knowledge,
            },
        )

    def _handle_general_banking_knowledge(self, input_text: str) -> str:
        knowledge = self._retrieve_knowledge(input_text)
        return self._generate(
            task="General Banking Knowledge",
            input_text=input_text,
            tool_context={"retrieved_knowledge": knowledge},
        )

    def _retrieve_knowledge(self, input_text: str) -> list[dict]:
        result = self.tools.run("knowledge.search", query=input_text, limit=5)
        return result.output

    def _search_web(self, input_text: str) -> list[dict]:
        result = self.tools.run("web.search", query=input_text, limit=3)
        return result.output

    def _generate(self, task: str, input_text: str, tool_context: object) -> str:
        system_prompt = (
            "You are BankingKnowledgeAgent for an internal finance and banking assistant. "
            "Help employees with document intelligence, research drafts, banking processes, "
            "and credit support. Answer in Vietnamese. Be concise, structured, and careful. "
            "Use retrieved internal knowledge when available. If retrieved knowledge is empty "
            "or insufficient, state that internal sources are missing and avoid inventing "
            "specific policies, numbers, or citations. Use web_search_results only as external "
            "context, and clearly separate it from internal knowledge."
        )
        user_prompt = (
            f"Task: {task}\n\n"
            f"User request:\n{input_text}\n\n"
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
