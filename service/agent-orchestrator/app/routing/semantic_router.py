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
    candidates: list[dict] | None = None
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
        result = self.evaluate(input_text)
        if result.intent == IntentType.unknown or result.confidence < self.threshold:
            return None
        return result

    def evaluate(self, input_text: str) -> SemanticIntentResult:
        text = input_text.strip()
        if not text:
            return SemanticIntentResult(intent=IntentType.unknown, confidence=0.0, candidates=[])

        try:
            self._ensure_example_vectors()
            if not self._example_vectors:
                return SemanticIntentResult(intent=IntentType.unknown, confidence=0.0, candidates=[])
            query_vector = self.embedding_client.embed(text)
        except Exception as exc:
            logger.warning("semantic_router_unavailable error=%s", exc)
            return SemanticIntentResult(intent=IntentType.unknown, confidence=0.0, candidates=[])

        scored_candidates: list[dict] = []
        for intent, example, example_vector in self._example_vectors:
            score = cosine_similarity(query_vector, example_vector)
            scored_candidates.append(
                {
                    "intent": intent.value,
                    "score": round(score, 4),
                    "example": example,
                }
            )

        top_candidates = sorted(
            scored_candidates,
            key=lambda candidate: float(candidate["score"]),
            reverse=True,
        )[:3]
        if not top_candidates:
            return SemanticIntentResult(intent=IntentType.unknown, confidence=0.0, candidates=[])

        best_candidate = top_candidates[0]
        return SemanticIntentResult(
            intent=IntentType(str(best_candidate["intent"])),
            confidence=float(best_candidate["score"]),
            matched_example=str(best_candidate["example"]),
            candidates=top_candidates,
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
