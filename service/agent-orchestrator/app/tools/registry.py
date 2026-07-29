from typing import Any
import time

from app.telemetry import record_tool_call, timed_ms
from app.tools.banking import (
    BankingProcessChecklistTool,
    DocumentExtractionTool,
    ResearchReportTemplateTool,
)
from app.tools.base import Tool, ToolResult
from app.tools.customer_data import CustomerDataMaskingTool, CustomerProfileChecklistTool
from app.tools.knowledge import KnowledgeSearchTool
from app.tools.web_search import WebSearchTool


class ToolRegistry:
    def __init__(self, tools: list[Tool] | None = None) -> None:
        self._tools: dict[str, Tool] = {}
        for tool in tools or []:
            self.register(tool)

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        return self._tools[name]

    def run(self, name: str, **kwargs: Any) -> ToolResult:
        start_time = time.perf_counter()
        try:
            result = self.get(name).run(**kwargs)
            record_tool_call(
                tool_name=name,
                input_json=kwargs,
                output_json=result.output,
                status="completed",
                duration_ms=timed_ms(start_time),
            )
            return result
        except Exception as exc:
            record_tool_call(
                tool_name=name,
                input_json=kwargs,
                output_json=None,
                status="failed",
                duration_ms=timed_ms(start_time),
                error_message=str(exc),
            )
            raise

    def list_tools(self) -> list[dict[str, str]]:
        return [
            {"name": tool.name, "description": tool.description}
            for tool in self._tools.values()
        ]


default_tool_registry = ToolRegistry(
    [
        CustomerDataMaskingTool(),
        CustomerProfileChecklistTool(),
        DocumentExtractionTool(),
        ResearchReportTemplateTool(),
        BankingProcessChecklistTool(),
        KnowledgeSearchTool(),
        WebSearchTool(),
    ]
)
