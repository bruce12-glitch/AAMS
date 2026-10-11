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


def test_detection_keeps_opencv_bgr_channel_order():
    """InsightFace performs its own channel swap; pass cv2 frames unchanged."""
    frame = np.zeros((2, 2, 3), dtype=np.uint8)
    frame[0, 0] = [10, 20, 30]

    class FakeAnalysis:
        received = None

        def get(self, image):
            self.received = image
            return []

    engine = object.__new__(FaceEngine)
    engine.app = FakeAnalysis()

    assert engine.detect_faces(frame) == []
    assert engine.app.received is frame
    assert engine.app.received[0, 0].tolist() == [10, 20, 30]


def test_identity_matching_does_not_construct_model(monkeypatch):
    """Vector lookup must not reload the heavyweight model per request."""
    import app.identity as identity

    class ModelMustNotInitialize:
        def __init__(self):
            raise AssertionError('IdentityVerifier initialized InsightFace')

        match_embeddings = staticmethod(FaceEngine.match_embeddings)
        find_best_match = staticmethod(FaceEngine.find_best_match)

    monkeypatch.setattr(identity, 'FaceEngine', ModelMustNotInitialize)
    verifier = identity.IdentityVerifier()
    assert verifier.face_engine is ModelMustNotInitialize
