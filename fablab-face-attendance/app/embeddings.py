"""
Pure-numpy embedding helpers.

Keep this module free of InsightFace / OpenCV so the API, identity
matching, and unit tests can run without downloading buffalo_l.
"""

from __future__ import annotations

import numpy as np

EMBED_DTYPE = np.float32
EMBED_DIM = 512


def as_embedding(value) -> np.ndarray:
    """Coerce list / bytes / ndarray to a unit-length float32 vector."""
    if value is None:
        raise ValueError("embedding is None")

    if isinstance(value, (bytes, bytearray, memoryview)):
        raw = np.frombuffer(value, dtype=EMBED_DTYPE)
        if raw.size != EMBED_DIM:
            # Legacy enroll/seed wrote float64 blobs
            raw = np.frombuffer(value, dtype=np.float64)
        vec = raw.astype(EMBED_DTYPE, copy=False)
    else:
        vec = np.asarray(value, dtype=EMBED_DTYPE).reshape(-1)

    if vec.size != EMBED_DIM:
        raise ValueError(f"expected {EMBED_DIM}-d embedding, got {vec.size}")

    norm = float(np.linalg.norm(vec))
    if norm > 0:
        vec = vec / norm
    return vec


def embedding_to_bytes(value) -> bytes:
    return as_embedding(value).astype(EMBED_DTYPE).tobytes()


def cosine_similarity(embedding_a, embedding_b) -> float:
    a = as_embedding(embedding_a)
    b = as_embedding(embedding_b)
    return float(np.clip(np.dot(a, b), -1.0, 1.0))


def max_similarity(query, gallery) -> float:
    """Max cosine of query vs an iterable of stored embeddings."""
    best = 0.0
    for item in gallery or []:
        if item is None:
            continue
        score = cosine_similarity(query, item)
        if score > best:
            best = score
    return best


def find_best_match(query, all_embeddings: dict, threshold: float = 0.45):
    """
    1:N search.

    all_embeddings: {user_id: [emb, emb, ...]}
    Returns (best_user_id or None, best_score).
    """
    best_user_id = None
    best_score = 0.0

    for user_id, gallery in (all_embeddings or {}).items():
        score = max_similarity(query, gallery)
        if score > best_score:
            best_score = score
            best_user_id = user_id

    if best_score < threshold:
        return None, best_score
    return best_user_id, best_score
