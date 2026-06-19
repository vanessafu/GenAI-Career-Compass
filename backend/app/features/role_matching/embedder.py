"""
CareerBERT embedding module.

Model_version 1:  BAAI/bge-base-en-v1.5(768-dim SentenceTransformer general)
Singleton — loaded once, reused across all requests.

Model JobBERT : input is restricted to 64 tokens, used for job title + skills 
Model bge-base-en-v1.5: input can be up to 512 tokens, used for longer CV text and role descriptions (first choice)
"""
from __future__ import annotations
import logging
from typing import Optional

logger = logging.getLogger("CareerCompass.Embedder")

MODEL_NAME = "BAAI/bge-base-en-v1.5"
EMBEDDING_DIM = 768

QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "
 
 
def _pick_device() -> str:
    """Prefer Apple Silicon GPU (Metal/MPS), then CUDA, then CPU."""
    import torch

    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"

class CareerEmbedder:
    """Thin wrapper that normalises embeddings to unit-length (cosine-ready)."""

    def __init__(self, model_name: str = MODEL_NAME, device: Optional[str] = None) -> None:
        from sentence_transformers import SentenceTransformer

        self.device = device or _pick_device()
        logger.info("Loading embedding model %s on %s", model_name, self.device)
        self._model = SentenceTransformer(model_name, device=self.device)
        logger.info("Embedding model ready.")
        
     # ---------- documents (roles): NO prefix ----------
    def encode_document(self, text: str) -> list[float]:
        vec = self._model.encode(text, normalize_embeddings=True)
        return vec.tolist()
 
    def encode_documents(self, texts: list[str], batch_size: int = 64) -> list[list[float]]:
        vecs = self._model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=len(texts) > 200,
        )
        return [v.tolist() for v in vecs]
 
    # ---------- queries (CV / interest): WITH prefix ----------
    def encode_query(self, text: str) -> list[float]:
        vec = self._model.encode(QUERY_INSTRUCTION + text, normalize_embeddings=True)
        return vec.tolist()
 
    def encode_queries(self, texts: list[str], batch_size: int = 64) -> list[list[float]]:
        prefixed = [QUERY_INSTRUCTION + t for t in texts]
        vecs = self._model.encode(
            prefixed,
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=len(texts) > 200,
        )
        return [v.tolist() for v in vecs]


_embedder: Optional[CareerEmbedder] = None


def get_embedder() -> CareerEmbedder:
    """Return the module-level singleton, loading the model on first call."""
    global _embedder
    if _embedder is None:
        _embedder = CareerEmbedder()
    return _embedder
