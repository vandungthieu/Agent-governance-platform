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
    embeddings: list[list[float]] | None = None,
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
        embedding = embeddings[index] if embeddings and index < len(embeddings) else None
        db.add(
            KnowledgeChunk(
                document_id=document.id,
                chunk_index=index,
                content=chunk,
                embedding=embedding,
                metadata_json={},
            )
        )

    db.commit()
    db.refresh(document)
    return document


def vector_to_sql_literal(vector: list[float]) -> str:
    return "[" + ",".join(f"{value:.8f}" for value in vector) + "]"


def search_knowledge_chunks_by_vector(
    db: Session,
    query_embedding: list[float],
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
            1 - (kc.embedding <=> CAST(:query_embedding AS vector)) AS similarity
        FROM knowledge_chunks kc
        JOIN knowledge_documents kd ON kd.id = kc.document_id
        WHERE
            kc.embedding IS NOT NULL
            AND (CAST(:document_type AS text) IS NULL OR kd.document_type = CAST(:document_type AS text))
        ORDER BY kc.embedding <=> CAST(:query_embedding AS vector)
        LIMIT :limit
        """
    )
    rows = db.execute(
        statement,
        {
            "query_embedding": vector_to_sql_literal(query_embedding),
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
            "similarity": float(row["similarity"] or 0),
            "rank": float(row["similarity"] or 0),
        }
        for row in rows
    ]


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
