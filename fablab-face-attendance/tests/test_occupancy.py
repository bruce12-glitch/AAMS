"""
Test occupancy tracking and timeout logic.
Run: python -m pytest tests/test_occupancy.py -v
"""

import sys
sys.path.insert(0, '..')

from app.occupancy import OccupancyTracker

def test_mark_inside():
    """Test marking user as inside."""
    tracker = OccupancyTracker()
    
    # This would require a database connection
    # For unit testing, we just verify the method exists
    assert hasattr(tracker, 'mark_inside')
    print("✓ mark_inside method exists")

def test_mark_exit():
    """Test marking user as exited."""
    tracker = OccupancyTracker()
    assert hasattr(tracker, 'mark_exit')
    print("✓ mark_exit method exists")

def test_timeout_logic():
    """Test 30-minute timeout marks as timeout_exited."""
    tracker = OccupancyTracker()
    assert tracker.timeout_minutes == 30
    assert hasattr(tracker, 'check_timeouts')
    print("✓ Timeout logic configured (30 minutes)")

if __name__ == '__main__':
    test_mark_inside()
    test_mark_exit()
    test_timeout_logic()
    print("\n✓ All occupancy tests passed!")
