"""
Alerts API Routes for FacePass FabLab.
Implements GET/POST alerts, admin approve.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix='/api/alerts', tags=['alerts'])

@router.get('')
async def list_alerts(severity: Optional[str] = None, alert_type: Optional[str] = None):
    """List alerts with optional filters."""
    from app.database import get_connection
    
    conn = get_connection()
    cursor = conn.cursor()
    
    query = 'SELECT * FROM alerts WHERE 1=1'
    params = []
    
    if severity:
        query += ' AND severity = ?'
        params.append(severity)
    
    if alert_type:
        query += ' AND alert_type = ?'
        params.append(alert_type)
    
    query += ' ORDER BY created_at DESC LIMIT 50'
    
    cursor.execute(query, params)
    alerts = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return {'alerts': alerts}

@router.post('/{alert_id}/approve')
async def approve_alert(alert_id: int):
    """Admin approve one-time entry."""
    from app.database import get_connection
    from datetime import datetime
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE alerts SET approved = 1, approved_at = ? WHERE id = ?
    ''', (datetime.now().isoformat(), alert_id))
    
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    
    if affected == 0:
        raise HTTPException(status_code=404, detail='Alert not found')
    
    return {'success': True}

@router.post('/{alert_id}/ack')
async def acknowledge_alert(alert_id: int):
    """Acknowledge alert."""
    from app.database import get_connection
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('UPDATE alerts SET acked = 1 WHERE id = ?', (alert_id,))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    
    if affected == 0:
        raise HTTPException(status_code=404, detail='Alert not found')
    
    return {'success': True}
