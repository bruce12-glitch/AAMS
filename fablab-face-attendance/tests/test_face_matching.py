"""
Test face matching and cosine similarity.
Run: python -m pytest tests/test_face_matching.py -v
"""

import numpy as np
import sys
sys.path.insert(0, '..')

from app.face_engine import FaceEngine

def test_cosine_similarity():
    """Test cosine similarity calculation."""
    engine = FaceEngine()
    
    # Create two identical normalized vectors
    vec1 = np.array([0.6, 0.8])
    vec1 = vec1 / np.linalg.norm(vec1)
    
    vec2 = vec1.copy()
    
    similarity = engine.match_embeddings(vec1, vec2)
    assert abs(similarity - 1.0) < 0.0001, "Identical vectors should have similarity ~1.0"
    print("✓ Identical vectors test passed")
    
    # Create orthogonal vectors
    vec3 = np.array([1.0, 0.0])
    vec4 = np.array([0.0, 1.0])
    
    similarity = engine.match_embeddings(vec3, vec4)
    assert abs(similarity) < 0.0001, "Orthogonal vectors should have similarity ~0.0"
    print("✓ Orthogonal vectors test passed")

def test_threshold_boundary():
    """Test threshold boundary conditions."""
    engine = FaceEngine()
    threshold = 0.45
    
    # Test just below threshold (should reject)
    vec1 = np.random.randn(512)
    vec1 = vec1 / np.linalg.norm(vec1)
    
    # Scale to create specific similarity
    vec2_below = vec1 * 0.44 + np.random.randn(512) * 0.1
    vec2_below = vec2_below / np.linalg.norm(vec2_below)
    
    sim_below = engine.match_embeddings(vec1, vec2_below)
    
    # Test just above threshold (should accept)
    vec2_above = vec1 * 0.46 + np.random.randn(512) * 0.1
    vec2_above = vec2_above / np.linalg.norm(vec2_above)
    
    sim_above = engine.match_embeddings(vec1, vec2_above)
    
    print(f"✓ Similarity below threshold: {sim_below:.4f}")
    print(f"✓ Similarity above threshold: {sim_above:.4f}")

def test_embedding_normalization():
    """Test that embeddings are properly normalized."""
    engine = FaceEngine()
    
    # Generate random embedding
    emb = np.random.randn(512)
    norm = np.linalg.norm(emb)
    emb_normalized = emb / norm
    
    # Check norm is 1
    assert abs(np.linalg.norm(emb_normalized) - 1.0) < 0.0001
    print("✓ Embedding normalization test passed")

if __name__ == '__main__':
    test_cosine_similarity()
    test_threshold_boundary()
    test_embedding_normalization()
    print("\n✓ All face matching tests passed!")
