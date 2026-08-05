from __future__ import annotations

import logging
import math
from dataclasses import dataclass

from app.rag.embeddings import EmbeddingClient
from app.routing.intent_examples import INTENT_EXAMPLES
from app.states.workflow import IntentType


logger = logging.getLogger("agent-orchestrator.semantic_router")


@dataclass(frozen=True)
class SemanticIntentResult:
    intent: IntentType
    confidence: float
    matched_example: str | None = None
    source: str = "semantic"


class SemanticIntentRouter:
    def __init__(
        self,
        embedding_client: EmbeddingClient | None = None,
        threshold: float = 0.72,
    ) -> None:
        self.embedding_client = embedding_client or EmbeddingClient()
        self.threshold = threshold
        self._example_vectors: list[tuple[IntentType, str, list[float]]] | None = None

    def route(self, input_text: str) -> SemanticIntentResult | None:
        text = input_text.strip()
        if not text:
            return None

        try:
            self._ensure_example_vectors()
            if not self._example_vectors:
                return None
            query_vector = self.embedding_client.embed(text)
        except Exception as exc:
            logger.warning("semantic_router_unavailable error=%s", exc)
            return None

        best_intent: IntentType | None = None
        best_example: str | None = None
        best_score = -1.0
        for intent, example, example_vector in self._example_vectors:
            score = cosine_similarity(query_vector, example_vector)
            if score > best_score:
                best_score = score
                best_intent = intent
                best_example = example

        if best_intent is None or best_score < self.threshold:
            return None
        return SemanticIntentResult(
            intent=best_intent,
            confidence=round(best_score, 4),
            matched_example=best_example,
        )

    def _ensure_example_vectors(self) -> None:
        if self._example_vectors is not None:
            return

        examples: list[tuple[IntentType, str]] = [
            (intent, example)
            for intent, intent_examples in INTENT_EXAMPLES.items()
            for example in intent_examples
        ]
        embeddings = self.embedding_client.embed_many(example for _, example in examples)
        self._example_vectors = [
            (intent, example, embedding)
            for (intent, example), embedding in zip(examples, embeddings, strict=False)
        ]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right, strict=False))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)
