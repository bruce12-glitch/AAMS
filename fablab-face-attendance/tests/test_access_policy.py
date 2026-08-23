"""
Test all 9 rows of the decision matrix (§11.2).
Run: python -m pytest tests/test_access_policy.py -v
"""

import sys
sys.path.insert(0, '..')

from app.access_policy import AccessDecision

def test_all_rows():
    """Test all 9 rows of the decision matrix."""
    policy = AccessDecision()
    
    # Row 1: Valid token + face matches + active payment + real → GRANT
    result = policy.evaluate_access('U1', {'result': 'MATCH', 'match': True}, 'active', 'real', 1)
    assert result['decision'] == 'GRANTED' and result['tag'] == 'authorized'
    print("✓ Row 1: Authorized entry")
    
    # Row 2: Valid token + face matches + expired payment + real → DENY + UNPAID
    result = policy.evaluate_access('U1', {'result': 'MATCH', 'match': True}, 'expired', 'real', 1)
    assert result['decision'] == 'DENIED' and result['tag'] == 'unpaid'
    print("✓ Row 2: Expired payment denied")
    
    # Row 3: Valid token + face mismatch + real → DENY + PROXY
    result = policy.evaluate_access('U1', {'result': 'PROXY'}, 'active', 'real', 1)
    assert result['decision'] == 'DENIED' and result['alert_type'] == 'PROXY'
    print("✓ Row 3: Proxy attempt detected")
    
    # Row 4: Valid token + no face → DENY + NOFACE
    result = policy.evaluate_access('U1', {}, 'active', 'real', 0)
    assert result['decision'] == 'DENIED' and result['tag'] == 'noface'
    print("✓ Row 4: No face detected")
    
    # Row 5: Invalid token + face recognized + active → Alert
    result = policy.evaluate_access(None, {'result': 'INVALID_TOKEN', 'detected_user': 'U2'}, 'active', 'real', 1)
    assert result['decision'] == 'DENIED'
    print("✓ Row 5: Invalid token with recognized face")
    
    # Row 6: Invalid token + face recognized + expired → DENY + UNPAID
    result = policy.evaluate_access(None, {'result': 'INVALID_TOKEN', 'detected_user': 'U2'}, 'expired', 'real', 1)
    assert result['decision'] == 'DENIED' and result['tag'] == 'unpaid'
    print("✓ Row 6: Invalid token with expired payment")
    
    # Row 7: Invalid token + unknown face → DENY + UNKNOWN
    result = policy.evaluate_access(None, {'result': 'UNKNOWN'}, 'active', 'real', 1)
    assert result['decision'] == 'DENIED' and result['tag'] == 'unknown'
    print("✓ Row 7: Unknown person")
    
    # Row 8: Any + spoof detected → DENY + SPOOF
    result = policy.evaluate_access('U1', {'result': 'MATCH'}, 'active', 'spoof', 1)
    assert result['decision'] == 'DENIED' and result['alert_type'] == 'SPOOF'
    print("✓ Row 8: Spoof attempt detected")
    
    # Row 9: Multiple faces → TAILGATE alert
    result = policy.evaluate_access('U1', {'result': 'MATCH'}, 'active', 'real', 3)
    assert result['alert_type'] == 'TAILGATE'
    print("✓ Row 9: Tailgating detected")
    
    print("\n✓ All 9 decision matrix rows tested successfully!")

if __name__ == '__main__':
    test_all_rows()
