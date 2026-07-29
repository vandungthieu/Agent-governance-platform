from typing import Any

from app.db.knowledge_repository import search_knowledge_chunks
from app.db.session import SessionLocal
from app.tools.base import ToolResult


class KnowledgeSearchTool:
    name = "knowledge.search"
    description = "Search internal knowledge documents stored for RAG context."

    def run(self, **kwargs: Any) -> ToolResult:
        query = str(kwargs.get("query", "")).strip()
        limit = int(kwargs.get("limit", 5))
        document_type = kwargs.get("document_type")

        if not query:
            return ToolResult(
                name=self.name,
                output=[],
                metadata={"result_count": 0, "reason": "empty_query"},
            )

        with SessionLocal() as db:
            results = search_knowledge_chunks(
                db=db,
                query=query,
                limit=limit,
                document_type=str(document_type) if document_type else None,
            )

        return ToolResult(
            name=self.name,
            output=results,
            metadata={"result_count": len(results)},
        )

