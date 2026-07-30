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
    parser.add_argument("--document-type", default="general", help="Document type, e.g. policy, faq, process")
    parser.add_argument("--source-uri", help="Original document URI or internal reference")
    parser.add_argument("--max-chars", type=int, default=1200)
    parser.add_argument("--overlap-chars", type=int, default=150)
    parser.add_argument("--skip-embeddings", action="store_true")
    args = parser.parse_args()

    path = Path(args.file_path)
    text = path.read_text(encoding="utf-8")
    chunks = chunk_text(text, max_chars=args.max_chars, overlap_chars=args.overlap_chars)
    embeddings = None if args.skip_embeddings else EmbeddingClient().embed_many(chunks)

    with SessionLocal() as db:
        document = create_knowledge_document(
            db=db,
            title=args.title or path.stem,
            document_type=args.document_type,
            source_uri=args.source_uri or str(path),
            chunks=chunks,
            embeddings=embeddings,
            metadata={"file_name": path.name},
        )

    embedding_status = "without embeddings" if args.skip_embeddings else "with embeddings"
    print(f"ingested document_id={document.id} chunks={len(chunks)} {embedding_status}")


if __name__ == "__main__":
    main()
