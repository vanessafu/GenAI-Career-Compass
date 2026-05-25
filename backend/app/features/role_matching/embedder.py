"""
CareerBERT embedding module.

Model: lwolfrum2/careerbert-jg  (768-dim SentenceTransformer)
Singleton — loaded once, reused across all requests.
"""
from __future__ import annotations

import logging
from typing import Optional

from sentence_transformers import SentenceTransformer

logger = logging.getLogger("CareerCompass.Embedder")

MODEL_NAME = "lwolfrum2/careerbert-jg"
EMBEDDING_DIM = 768


class CareerEmbedder:
    """Thin wrapper that normalises embeddings to unit-length (cosine-ready)."""

    def __init__(self, model_name: str = MODEL_NAME) -> None:
        logger.info("Loading embedding model: %s", model_name)
        self._model = SentenceTransformer(model_name)
        logger.info("Embedding model ready.")

    def encode(self, text: str) -> list[float]:
        return self._model.encode(text, normalize_embeddings=True).tolist()

    def encode_batch(self, texts: list[str], batch_size: int = 64) -> list[list[float]]:
        embeddings = self._model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=len(texts) > 200,
        )
        return [e.tolist() for e in embeddings]


_embedder: Optional[CareerEmbedder] = None


def get_embedder() -> CareerEmbedder:
    """Return the module-level singleton, loading the model on first call."""
    global _embedder
    if _embedder is None:
        _embedder = CareerEmbedder()
    return _embedder
