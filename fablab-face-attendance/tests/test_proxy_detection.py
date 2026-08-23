"""
Test proxy detection logic.
Run: python -m pytest tests/test_proxy_detection.py -v
"""

import sys
sys.path.insert(0, '..')

from app.access_policy import AccessDecision

def test_proxy_detection():
    """Test claimed_id ≠ detected_face → PROXY result."""
    policy = AccessDecision()
    
    face_result = {
        'result': 'PROXY',
        'match': False,
        'similarity': 0.32,
        'claimed_user': {'user_id': 'RA2111003010123', 'name': 'Rahul Kumar'},
        'detected_user': 'RA2111003010126'
    }
    
    result = policy.evaluate_access(
        claimed_id='RA2111003010123',
        face_result=face_result,
        payment_status='active',
        liveness_status='real',
        face_count=1
    )
    
    assert result['decision'] == 'DENIED'
    assert result['alert_type'] == 'PROXY'
    assert result['tag'] == 'proxy'
    print("✓ Proxy detection test passed")

def test_match_result():
    """Test claimed_id = detected_face → MATCH result."""
    policy = AccessDecision()
    
    face_result = {
        'result': 'MATCH',
        'match': True,
        'similarity': 0.89,
        'claimed_user': {'user_id': 'RA2111003010123', 'name': 'Rahul Kumar'},
        'detected_user': 'RA2111003010123'
    }
    
    result = policy.evaluate_access(
        claimed_id='RA2111003010123',
        face_result=face_result,
        payment_status='active',
        liveness_status='real',
        face_count=1
    )
    
    assert result['decision'] == 'GRANTED'
    assert result['alert_type'] is None
    assert result['tag'] == 'authorized'
    print("✓ Match result test passed")

def test_unknown_face_with_valid_token():
    """Test unknown face with valid token → UNKNOWN result."""
    policy = AccessDecision()
    
    face_result = {
        'result': 'UNKNOWN',
        'match': False,
        'similarity': 0.25,
        'claimed_user': {'user_id': 'RA2111003010123'},
        'detected_user': None
    }
    
    result = policy.evaluate_access(
        claimed_id='RA2111003010123',
        face_result=face_result,
        payment_status='active',
        liveness_status='real',
        face_count=1
    )
    
    assert result['decision'] == 'DENIED'
    assert result['alert_type'] == 'UNKNOWN'
    assert result['tag'] == 'unknown'
    print("✓ Unknown face with valid token test passed")

if __name__ == '__main__':
    test_proxy_detection()
    test_match_result()
    test_unknown_face_with_valid_token()
    print("\n✓ All proxy detection tests passed!")
