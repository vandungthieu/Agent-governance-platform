import re
import unicodedata
from typing import Any

from app.db.knowledge_repository import search_knowledge_chunks
from app.db.knowledge_repository import search_knowledge_chunks_by_vector
from app.db.session import SessionLocal
from app.rag.embeddings import EmbeddingClient
from app.tools.base import ToolResult


class KnowledgeSearchTool:
    name = "knowledge.search"
    description = "Search internal knowledge documents stored for RAG context."

    def run(self, **kwargs: Any) -> ToolResult:
        query = str(kwargs.get("query", "")).strip()
        limit = int(kwargs.get("limit", 5))
        retrieval_limit = max(limit * 3, 12)
        document_type = kwargs.get("document_type")

        if not query:
            return ToolResult(
                name=self.name,
                output=[],
                metadata={"result_count": 0, "reason": "empty_query"},
            )

        with SessionLocal() as db:
            try:
                query_embedding = EmbeddingClient().embed(query)
                results = search_knowledge_chunks_by_vector(
                    db=db,
                    query_embedding=query_embedding,
                    limit=retrieval_limit,
                    document_type=str(document_type) if document_type else None,
                )
                search_mode = "vector"
            except Exception as exc:
                results = search_knowledge_chunks(
                    db=db,
                    query=query,
                    limit=limit,
                    document_type=str(document_type) if document_type else None,
                )
                search_mode = "text"
                error_message = str(exc)

        results = rerank_results(query=query, results=results)[:limit]
        metadata: dict[str, Any] = {"result_count": len(results), "search_mode": search_mode}
        if search_mode == "text":
            metadata["vector_error"] = error_message

        return ToolResult(
            name=self.name,
            output=results,
            metadata=metadata,
        )


def normalize_text(value: str) -> str:
    value = value.replace("Đ", "D").replace("đ", "d")
    without_accents = "".join(
        character
        for character in unicodedata.normalize("NFD", value.lower())
        if unicodedata.category(character) != "Mn"
    )
    return re.sub(r"[^a-z0-9]+", " ", without_accents)


def tokenize(value: str) -> set[str]:
    return {token for token in normalize_text(value).split() if len(token) >= 2}


def expand_query(value: str) -> str:
    normalized = normalize_text(value)
    expansions = []
    if "sinh nam" in normalized or "nam sinh" in normalized:
        expansions.append("ngay sinh")
    if "the" in normalized:
        expansions.append("card atm debit visa")
    return " ".join([value, *expansions])


def ngrams(tokens: list[str], min_size: int = 2, max_size: int = 4) -> set[str]:
    phrases: set[str] = set()
    for size in range(min_size, max_size + 1):
        for index in range(0, max(len(tokens) - size + 1, 0)):
            phrases.add(" ".join(tokens[index : index + size]))
    return phrases


def rerank_results(query: str, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    expanded_query = expand_query(query)
    query_tokens = tokenize(expanded_query)
    if not query_tokens:
        return results
    query_token_list = normalize_text(expanded_query).split()
    query_phrases = ngrams(query_token_list)

    for result in results:
        searchable_text = " ".join(
            str(result.get(key) or "")
            for key in ("title", "document_type", "source_uri", "content")
        )
        normalized_searchable_text = normalize_text(searchable_text)
        content_tokens = tokenize(searchable_text)
        overlap = query_tokens & content_tokens
        lexical_score = len(overlap) / len(query_tokens)
        phrase_score = sum(1 for phrase in query_phrases if phrase in normalized_searchable_text)
        base_score = float(result.get("similarity", result.get("rank", 0)) or 0)
        lexical_score = lexical_score + (phrase_score * 0.2)
        result["lexical_score"] = lexical_score
        result["rerank_score"] = base_score + lexical_score

    return sorted(
        results,
        key=lambda result: (
            float(result.get("rerank_score", 0)),
            float(result.get("similarity", result.get("rank", 0)) or 0),
        ),
        reverse=True,
    )
