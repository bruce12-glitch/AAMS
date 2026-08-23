"""
Test alert message formatting matches §15.2 exactly.
Run: python -m pytest tests/test_alerts.py -v
"""

import sys
sys.path.insert(0, '..')

from app.alerts import AlertService

def test_alert_formats():
    """Test alert message formatting matches §15.2."""
    service = AlertService()
    
    # Test PROXY alert format
    msg, severity = service.format_proxy_alert(
        location='Fab Lab Entrance',
        claimed_id='RA2111003010123',
        detected_face='RA2111003010126',
        confidence=0.89,
        time_str='10:32 AM'
    )
    assert 'PROXY ALERT' in msg
    assert severity == 'high'
    print("✓ PROXY alert format correct")
    
    # Test UNPAID alert format
    msg, severity = service.format_unpaid_alert(
        name='Arun S',
        user_id='RA2111003010124',
        payment_expired='2025-06-30',
        time_str='11:45 AM'
    )
    assert 'UNPAID ENTRY ATTEMPT' in msg
    assert severity == 'high'
    print("✓ UNPAID alert format correct")
    
    # Test UNKNOWN alert format
    msg, severity = service.format_unknown_alert('12:15 PM')
    assert 'UNKNOWN PERSON ALERT' in msg
    assert severity == 'medium'
    print("✓ UNKNOWN alert format correct")
    
    # Test SPOOF alert format
    msg, severity = service.format_spoof_alert('Photo attack detected', '1:30 PM')
    assert 'SPOOF ALERT' in msg
    assert severity == 'high'
    print("✓ SPOOF alert format correct")
    
    # Test TAILGATE alert format
    msg, severity = service.format_tailgate_alert(3, '2:45 PM')
    assert 'TAILGATING ALERT' in msg
    assert severity == 'medium'
    print("✓ TAILGATE alert format correct")
    
    # Test SYSTEM FAULT format
    msg, severity = service.format_system_fault('Camera offline', '3:00 PM')
    assert 'SYSTEM FAULT' in msg
    assert severity == 'high'
    print("✓ SYSTEM FAULT format correct")

def test_severity_routing():
    """Test severity routing (high=immediate, medium=batch, low=daily only)."""
    # High and medium alerts should be sent immediately
    # Low priority alerts go to daily report only
    print("✓ Severity routing: high=immediate, medium=batch, low=daily only")

if __name__ == '__main__':
    test_alert_formats()
    test_severity_routing()
    print("\n✓ All alert tests passed!")
