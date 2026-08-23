"""Pure embedding helpers — no InsightFace required."""

import numpy as np

from app.embeddings import cosine_similarity, embedding_to_bytes, as_embedding, find_best_match


def test_identical_vectors():
    vec = np.array([0.6, 0.8] + [0.0] * 510, dtype=np.float32)
    assert abs(cosine_similarity(vec, vec) - 1.0) < 1e-5


def test_orthogonal_vectors():
    a = np.zeros(512, dtype=np.float32)
    b = np.zeros(512, dtype=np.float32)
    a[0] = 1
    b[1] = 1
    assert abs(cosine_similarity(a, b)) < 1e-5


def test_roundtrip_bytes():
    vec = np.random.randn(512).astype(np.float32)
    vec = vec / np.linalg.norm(vec)
    back = as_embedding(embedding_to_bytes(vec))
    assert abs(cosine_similarity(vec, back) - 1.0) < 1e-5


def test_find_best_match_threshold():
    gallery = {
        "U1": [np.eye(512, dtype=np.float32)[0]],
        "U2": [np.eye(512, dtype=np.float32)[1]],
    }
    query = np.eye(512, dtype=np.float32)[0]
    uid, score = find_best_match(query, gallery, threshold=0.45)
    assert uid == "U1"
    assert score > 0.99
