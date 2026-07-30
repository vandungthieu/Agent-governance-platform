from __future__ import annotations

from typing import Iterable

import httpx

from app.core.config import settings


class EmbeddingClient:
    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model = model or settings.OLLAMA_EMBEDDING_MODEL
        self.timeout_seconds = timeout_seconds or settings.EMBEDDING_TIMEOUT_SECONDS

    def embed(self, text: str) -> list[float]:
        embeddings = self.embed_many([text])
        return embeddings[0]

    def embed_many(self, texts: Iterable[str]) -> list[list[float]]:
        inputs = [text.strip() for text in texts]
        if not inputs:
            return []

        response = httpx.post(
            f"{self.base_url}/api/embed",
            json={"model": self.model, "input": inputs},
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        embeddings = payload.get("embeddings")
        if not isinstance(embeddings, list):
            raise ValueError("Ollama embedding response did not include embeddings")

        return [self._normalize_embedding(embedding) for embedding in embeddings]

    @staticmethod
    def _normalize_embedding(embedding: object) -> list[float]:
        if not isinstance(embedding, list):
            raise ValueError("Embedding must be a list of floats")
        return [float(value) for value in embedding]
