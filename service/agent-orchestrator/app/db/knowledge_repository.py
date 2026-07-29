from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.models import KnowledgeChunk, KnowledgeDocument


def create_knowledge_document(
    db: Session,
    title: str,
    document_type: str,
    source_uri: str | None,
    chunks: list[str],
    metadata: dict[str, Any] | None = None,
) -> KnowledgeDocument:
    document = KnowledgeDocument(
        title=title,
        document_type=document_type,
        source_uri=source_uri,
        metadata_json=metadata or {},
    )
    db.add(document)
    db.flush()

    for index, chunk in enumerate(chunks):
        db.add(
            KnowledgeChunk(
                document_id=document.id,
                chunk_index=index,
                content=chunk,
                metadata_json={},
            )
        )

    db.commit()
    db.refresh(document)
    return document


def search_knowledge_chunks(
    db: Session,
    query: str,
    limit: int = 5,
    document_type: str | None = None,
) -> list[dict[str, Any]]:
    statement = text(
        """
        SELECT
            kc.id,
            kc.document_id,
            kc.chunk_index,
            kc.content,
            kd.title,
            kd.document_type,
            kd.source_uri,
            ts_rank(
                to_tsvector('simple', coalesce(kd.title, '') || ' ' || coalesce(kc.content, '')),
                plainto_tsquery('simple', :query)
            ) AS rank
        FROM knowledge_chunks kc
        JOIN knowledge_documents kd ON kd.id = kc.document_id
        WHERE
            (CAST(:document_type AS text) IS NULL OR kd.document_type = CAST(:document_type AS text))
            AND (
                to_tsvector('simple', coalesce(kd.title, '') || ' ' || coalesce(kc.content, ''))
                    @@ plainto_tsquery('simple', :query)
                OR kc.content ILIKE :like_query
                OR kd.title ILIKE :like_query
            )
        ORDER BY rank DESC, kc.created_at DESC
        LIMIT :limit
        """
    )
    rows = db.execute(
        statement,
        {
            "query": query,
            "like_query": f"%{query}%",
            "limit": limit,
            "document_type": document_type,
        },
    ).mappings()

    return [
        {
            "chunk_id": str(row["id"]),
            "document_id": str(row["document_id"]),
            "chunk_index": row["chunk_index"],
            "title": row["title"],
            "document_type": row["document_type"],
            "source_uri": row["source_uri"],
            "content": row["content"],
            "rank": float(row["rank"] or 0),
        }
        for row in rows
    ]
