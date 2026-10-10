"""Embedding backends.

* sentence-transformers: real semantic embeddings (downloads a small model once).
* hash: tiny offline fallback (bag-of-words hashing). Used in tests and if the
  model cannot be loaded. Not as smart, but needs no download.
"""
import hashlib
import logging
import math
import re

from app.config import settings

logger = logging.getLogger(__name__)
_DIM = 384
_STOP = {"the", "a", "an", "and", "or", "of", "to", "in", "with", "for", "on", "is", "are", "who", "has", "have", "find", "me"}


class HashEmbedder:
    name = "hash384"

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._one(t) for t in texts]

    def _one(self, text: str) -> list[float]:
        vec = [0.0] * _DIM
        tokens = [t for t in re.findall(r"[a-z0-9+#.]+", text.lower()) if t not in _STOP]
        for token in tokens:
            h = int(hashlib.md5(token.encode()).hexdigest(), 16)
            vec[h % _DIM] += 1.0
        vec = [math.log1p(v) for v in vec]
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]


class SentenceTransformerEmbedder:
    def __init__(self, model_name: str):
        from sentence_transformers import SentenceTransformer  # heavy import, loaded lazily
        self._model = SentenceTransformer(model_name)
        self.name = "st_" + re.sub(r"[^A-Za-z0-9_-]", "_", model_name)

    def embed(self, texts: list[str]) -> list[list[float]]:
        return self._model.encode(texts, normalize_embeddings=True).tolist()


_cache: dict = {}


def get_embedder():
    backend, model = settings.embedding_backend, settings.embedding_model
    key = (backend, model)
    if key not in _cache:
        if backend == "hash":
            _cache[key] = HashEmbedder()
        else:
            try:
                _cache[key] = SentenceTransformerEmbedder(model)
            except Exception as exc:  # model missing, no internet, library not installed...
                logger.warning("Could not load '%s' (%s). Falling back to hash embeddings.", model, exc)
                _cache[key] = HashEmbedder()
    return _cache[key]
