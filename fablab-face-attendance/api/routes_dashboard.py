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
    """Get live camera status plus the most recent entry event."""
    from app.camera import CameraManager
    from app.database import get_connection

    camera_status = CameraManager().get_status()

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM entry_logs ORDER BY event_time DESC LIMIT 1')
    row = cursor.fetchone()
    conn.close()

    current = dict(row) if row else None
    return {
        'camera': camera_status,
        'current_event': current,
        'steps': [
            'TOKEN_DETECTED', 'FACE_DETECTED', 'QUALITY', 'EMBEDDING',
            'MATCH', 'LIVENESS', 'PAYMENT', 'DECISION',
        ],
        'mode': 'prototype-live',
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
