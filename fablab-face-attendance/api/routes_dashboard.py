"""
Dashboard API Routes for FacePass FabLab.
Implements GET stats, live-status, activity, research.
"""

from fastapi import APIRouter

router = APIRouter(prefix='/api/dashboard', tags=['dashboard'])

@router.get('/stats')
async def get_stats():
    """Get KPI stats (entries, inside, alerts, members)."""
    from app.database import get_connection
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Total entries today
    from datetime import datetime
    today = datetime.now().strftime('%Y-%m-%d')
    cursor.execute('''
        SELECT COUNT(*) FROM entry_logs WHERE DATE(event_time) = ?
    ''', (today,))
    total_entries = cursor.fetchone()[0]
    
    # Currently inside
    cursor.execute('SELECT COUNT(*) FROM occupants WHERE status = \'inside\'')
    inside_count = cursor.fetchone()[0]
    
    # Unacknowledged alerts
    cursor.execute('SELECT COUNT(*) FROM alerts WHERE acked = 0')
    alert_count = cursor.fetchone()[0]
    
    # Active members
    cursor.execute('SELECT COUNT(*) FROM users WHERE active = 1 AND payment_status = \'active\'')
    member_count = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        'total_entries': total_entries,
        'inside_count': inside_count,
        'alert_count': alert_count,
        'member_count': member_count
    }

@router.get('/activity')
async def get_activity():
    """Get recent activity feed."""
    from app.database import get_connection
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM entry_logs ORDER BY event_time DESC LIMIT 20
    ''')
    activities = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return {'activities': activities}

@router.get('/live')
async def get_live_status():
    """Get live camera status, current event, steps.

    Previously this constructed a brand-new CameraManager and read its status
    without ever calling start(), so `running` was always False and the
    console permanently showed "camera standby" even with a working camera.
    Now it reports the shared capture service, which owns the real device.
    """
    from app.capture_service import get_capture_service

    status = get_capture_service().get_status()
    last = status.get('last_event')

    steps = ['IDLE']
    if last:
        steps = ['FACE_DETECTED', 'MATCHED', 'DECISION_MADE']

    return {
        'camera': {
            # The console keys off `status == 'online'` or fps > 0.
            'status': 'online' if status['online'] else 'offline',
            'source': status.get('source'),
            'fps': status.get('fps') or 0,
            'resolution': status.get('resolution'),
            'frames_processed': status.get('frames_processed', 0),
        },
        'current_event': last,
        'steps': steps,
    }

@router.get('/research')
async def get_research_data():
    """Get threshold calibration data for research page."""
    return {
        'match_threshold': 0.45,
        'blur_threshold': 100,
        'min_face_size': 120,
        'brightness_range': [40, 220],
        'pose_limits': {'yaw': 25, 'pitch': 20, 'roll': 20}
    }


@router.get('/latency')
async def get_latency_metrics():
    """
    Decision-latency metrics (§23.3, target < 3000 ms).
    Aggregates the most recent logged entry attempts.
    """
    from app.database import get_connection

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT latency_ms FROM entry_logs
        WHERE latency_ms IS NOT NULL
        ORDER BY id DESC LIMIT 200
    ''')
    values = [row[0] for row in cursor.fetchall()]
    conn.close()

    if not values:
        return {'samples': 0, 'avg_ms': None, 'p95_ms': None,
                'target_ms': 3000, 'within_target': None}

    ordered = sorted(values)
    p95 = ordered[max(0, int(len(ordered) * 0.95) - 1)]
    avg = sum(values) / len(values)
    return {
        'samples': len(values),
        'avg_ms': round(avg, 1),
        'p95_ms': round(float(p95), 1),
        'max_ms': round(float(max(values)), 1),
        'target_ms': 3000,
        'within_target': bool(p95 <= 3000)
    }
