from __future__ import annotations

import argparse
from pathlib import Path

from app.db.knowledge_repository import create_knowledge_document
from app.db.session import SessionLocal
from app.rag.chunking import chunk_text
from app.rag.embeddings import EmbeddingClient


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest a text or markdown file into RAG storage.")
    parser.add_argument("file_path", help="Path to .txt or .md file")
    parser.add_argument("--title", help="Document title")
    parser.add_argument("--document-type", help="Document type, e.g. owner_profile, banking_faq, process")
    parser.add_argument("--source-uri", help="Original document URI or internal reference")
    parser.add_argument("--max-chars", type=int, default=1200)
    parser.add_argument("--overlap-chars", type=int, default=150)
    parser.add_argument("--skip-embeddings", action="store_true")
    args = parser.parse_args()

    path = Path(args.file_path)
    text = path.read_text(encoding="utf-8")
    document_type = args.document_type or infer_document_type(path)
    chunks = chunk_text(text, max_chars=args.max_chars, overlap_chars=args.overlap_chars)
    embeddings = None if args.skip_embeddings else EmbeddingClient().embed_many(chunks)

    with SessionLocal() as db:
        document = create_knowledge_document(
            db=db,
            title=args.title or path.stem,
            document_type=document_type,
            source_uri=args.source_uri or str(path),
            chunks=chunks,
            embeddings=embeddings,
            metadata={"file_name": path.name},
        )

    embedding_status = "without embeddings" if args.skip_embeddings else "with embeddings"
    print(f"ingested document_id={document.id} document_type={document_type} chunks={len(chunks)} {embedding_status}")


def infer_document_type(path: Path) -> str:
    normalized_name = path.stem.lower().replace("-", "_")
    if "owner" in normalized_name or "founder" in normalized_name:
        return "owner_profile"
    if "account_opening" in normalized_name or "faq" in normalized_name:
        return "banking_faq"
    if "process" in normalized_name or "procedure" in normalized_name:
        return "process"
    if "customer" in normalized_name:
        return "customer_profile"
    return "general"


if __name__ == "__main__":
    main()
