"""ChromaDB wrapper: store resume chunks and search them."""
import logging
import re

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import settings
from app.exceptions import VectorStoreError
from app.rag.embeddings import get_embedder

logger = logging.getLogger(__name__)
_clients: dict = {}


def _collection():
    path = str(settings.chroma_dir)
    try:
        client = _clients.get(path)
        if client is None:
            settings.chroma_dir.mkdir(parents=True, exist_ok=True)
            client = chromadb.PersistentClient(
                path=path, settings=ChromaSettings(anonymized_telemetry=False))
            _clients[path] = client
        # one collection per embedding model, so vectors from different models never mix
        name = "resumes_" + re.sub(r"[^A-Za-z0-9_-]", "_", get_embedder().name)[:50]
        return client.get_or_create_collection(name=name, metadata={"hnsw:space": "cosine"})
    except Exception as exc:
        logger.error("ChromaDB error: %s", exc)
        raise VectorStoreError("The vector database is unavailable.") from exc


def add_candidate_chunks(candidate_id: int, candidate_name: str, chunks: list[str]) -> None:
    if not chunks:
        raise VectorStoreError("No text chunks to index.")
    try:
        col = _collection()
        col.add(
            ids=[f"cand{candidate_id}_chunk{i}" for i in range(len(chunks))],
            documents=chunks,
            embeddings=get_embedder().embed(chunks),
            metadatas=[{"candidate_id": candidate_id, "candidate_name": candidate_name,
                        "chunk_index": i} for i in range(len(chunks))],
        )
    except VectorStoreError:
        raise
    except Exception as exc:
        logger.error("Indexing failed: %s", exc)
        raise VectorStoreError("Failed to index the resume.") from exc


def search_chunks(query: str, top_k: int = 5, candidate_ids: list[int] | None = None) -> list[dict]:
    """Return the most relevant chunks, best first. Empty list if nothing is indexed."""
    col = _collection()
    try:
        count = col.count()
        if count == 0:
            return []
        kwargs = {
            "query_embeddings": get_embedder().embed([query]),
            "n_results": min(top_k, count),
            "include": ["documents", "metadatas", "distances"],
        }
        if candidate_ids:
            kwargs["where"] = {"candidate_id": {"$in": [int(i) for i in candidate_ids]}}
        res = col.query(**kwargs)
    except Exception as exc:
        logger.error("Vector search failed: %s", exc)
        raise VectorStoreError("Candidate search failed.") from exc
    hits = []
    for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
        hits.append({"candidate_id": int(meta["candidate_id"]), "text": doc,
                     "chunk_index": meta.get("chunk_index", 0),
                     "score": max(0.0, min(1.0, 1.0 - float(dist)))})
    return hits


def get_candidate_chunks(candidate_id: int, limit: int = 6) -> list[dict]:
    col = _collection()
    try:
        res = col.get(where={"candidate_id": int(candidate_id)}, limit=limit,
                      include=["documents", "metadatas"])
    except Exception as exc:
        raise VectorStoreError("Could not read resume chunks.") from exc
    items = [{"text": d, "chunk_index": m.get("chunk_index", 0)}
             for d, m in zip(res["documents"], res["metadatas"])]
    return sorted(items, key=lambda x: x["chunk_index"])


def delete_candidate_chunks(candidate_id: int) -> None:
    col = _collection()
    try:
        col.delete(where={"candidate_id": int(candidate_id)})
    except Exception as exc:
        raise VectorStoreError("Could not remove resume chunks.") from exc
