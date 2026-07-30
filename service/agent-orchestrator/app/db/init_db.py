from app.db import models  # noqa: F401
from app.db.session import Base, engine
from app.core.config import settings
from sqlalchemy import text


def init_db() -> None:
    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        connection.execute(
            text(
                f"""
                ALTER TABLE knowledge_chunks
                ADD COLUMN IF NOT EXISTS embedding vector({settings.EMBEDDING_DIMENSIONS})
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_embedding_hnsw
                ON knowledge_chunks
                USING hnsw (embedding vector_cosine_ops)
                WHERE embedding IS NOT NULL
                """
            )
        )


if __name__ == "__main__":
    init_db()
