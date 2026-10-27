"""
Alerts API Routes for FacePass FabLab.
Implements GET/POST alerts, admin approve.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, Literal
from app.event_records import RecordScope, scope_sql, source_counts, SECURITY_ALERTS

from app.security import require_admin, require_user

router = APIRouter(prefix='/api/alerts', tags=['alerts'])

@router.get('')
async def list_alerts(severity: Optional[str] = None, alert_type: Optional[str] = None,
                      scope: RecordScope = 'all', status: Literal['all', 'open', 'reviewed'] = 'all',
                      _: dict = Depends(require_user)):
    """List alerts with optional filters."""
    from app.database import get_connection
    
    conn = get_connection()
    cursor = conn.cursor()
    
    query = '''SELECT a.*, e.claimed_id, e.recognized_id, e.reason AS decision_reason,
                      e.decision, e.similarity, e.comparison_performed, e.liveness_status,
                      u.name AS recognized_name, c.name AS claimed_name
               FROM alerts a
               LEFT JOIN entry_logs e ON e.id=a.entry_log_id
               LEFT JOIN users u ON u.user_id=e.recognized_id
               LEFT JOIN users c ON c.user_id=e.claimed_id
               WHERE a.''' + SECURITY_ALERTS + ' AND ' + scope_sql(scope, 'a.event_source')
    params = []
    
    if severity:
        query += ' AND a.severity = ?'
        params.append(severity)
    
    if alert_type:
        query += ' AND a.alert_type = ?'
        params.append(alert_type)
    
    if status != 'all':
        query += ' AND a.acked = ?'
        params.append(int(status == 'reviewed'))
    query += ' ORDER BY a.id DESC LIMIT 100'
    
    cursor.execute(query, params)
    alerts = [dict(row) for row in cursor.fetchall()]
    counts = source_counts(conn, 'alerts', SECURITY_ALERTS)
    conn.close()
    
    return {'alerts': alerts, 'source_counts': counts, 'scope': scope}

@router.post('/{alert_id}/approve')
async def approve_alert(alert_id: int, _: None = Depends(require_admin)):
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
async def acknowledge_alert(alert_id: int, _: None = Depends(require_admin)):
    """Acknowledge alert (admin token: otherwise anyone could clear the board)."""
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
