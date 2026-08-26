"""
Test face matching and cosine similarity (pure math — no models needed).
Run: python -m pytest tests/test_face_matching.py -v
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np

from app.face_engine import FaceEngine


def test_cosine_similarity():
    """Identical vectors -> ~1.0; orthogonal -> ~0.0; opposite -> ~-1.0."""
    vec = np.array([0.6, 0.8])
    vec = vec / np.linalg.norm(vec)

    same = FaceEngine.match_embeddings(vec, vec.copy())
    assert abs(same - 1.0) < 1e-4, "identical vectors should score ~1.0"

    ortho = FaceEngine.match_embeddings(np.array([1.0, 0.0]), np.array([0.0, 1.0]))
    assert abs(ortho) < 1e-4, "orthogonal vectors should score ~0.0"

    opposite = FaceEngine.match_embeddings(vec, -vec)
    assert abs(opposite + 1.0) < 1e-4, "opposite vectors should score ~-1.0"


def test_threshold_boundary():
    """Noisy variants of one vector stay above 0.45; different vectors below."""
    rng = np.random.default_rng(7)
    anchor = rng.normal(size=512)
    anchor /= np.linalg.norm(anchor)

    near = anchor + rng.normal(scale=0.05, size=512)
    near /= np.linalg.norm(near)
    sim_near = FaceEngine.match_embeddings(anchor, near)
    assert sim_near > 0.45, f"near-duplicate scored {sim_near:.3f}, expected match"

    other = rng.normal(size=512)
    other /= np.linalg.norm(other)
    sim_other = FaceEngine.match_embeddings(anchor, other)
    assert sim_other < 0.45, f"random impostor scored {sim_other:.3f}, expected reject"
    assert sim_near > sim_other


def test_embedding_normalization():
    """Contract: callers normalize inputs (identity.py does). With normalized
    inputs, the score is magnitude-invariant — scaling must not move it."""
    rng = np.random.default_rng(3)
    unit = rng.normal(size=512)
    unit /= np.linalg.norm(unit)
    reference = np.roll(unit, 1)  # deterministic "different" vector

    base = FaceEngine.match_embeddings(unit, reference / np.linalg.norm(reference))
    for scale in (5.0, 0.2):
        scaled = reference * scale
        score = FaceEngine.match_embeddings(unit, scaled / np.linalg.norm(scaled))
        assert abs(base - score) < 1e-9, "normalized-input scores must be scale-invariant"
