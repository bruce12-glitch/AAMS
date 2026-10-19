"""
Admin API Routes for FacePass FabLab.
Implements admin actions, exceptions log.
Mutating endpoints require X-Admin-Token (§27.2).
"""

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Literal

from app.security import require_admin, require_user

router = APIRouter(prefix='/api/admin', tags=['admin'])


class ExceptionLog(BaseModel):
    action: str
    target_user_id: str
    reason: str


class PaymentUpdate(BaseModel):
    user_id: str
    payment_status: Literal['active', 'pending', 'expired', 'inactive']


@router.get('/readiness')
async def prototype_readiness(_: dict = Depends(require_admin)):
    """Local setup checks; configured credentials are never returned."""
    from app.database import get_connection
    from app.vision import engine_state
    from app.config import get_telegram_config
    from app.alerts import configured

    conn = get_connection()
    try:
        total, enrolled = conn.execute('''
            SELECT COUNT(*), COALESCE(SUM(
                CASE WHEN length(face_embedding)>0 OR length(face_embedding_2)>0
                     OR length(face_embedding_3)>0 THEN 1 ELSE 0 END), 0)
            FROM users WHERE active=1
        ''').fetchone()
        last_sent = conn.execute("SELECT MAX(sent_at) FROM alerts WHERE sent_status='sent'").fetchone()[0]
    finally:
        conn.close()
    cfg = get_telegram_config()
    return {
        'database': 'ready', 'cv_engine': engine_state(),
        'active_members': total, 'enrolled_members': enrolled,
        'telegram': {
            'configured': bool(cfg.get('enabled') and configured(cfg.get('bot_token'))
                               and configured(cfg.get('chat_id'))),
            'last_sent_at': last_sent,
        },
    }


@router.post('/vision/warmup', status_code=202)
async def warmup_vision(request: Request, _: dict = Depends(require_admin)):
    """Download/load the model without blocking health or other requests."""
    from app.vision import engine_state, get_engine, VisionUnavailableError

    if engine_state() == 'ready':
        return {'cv_engine': 'ready'}
    task = getattr(request.app.state, 'vision_warmup_task', None)
    if task is None or task.done():
        async def initialize():
            try:
                await asyncio.to_thread(get_engine, retry=True)
            except VisionUnavailableError:
                pass  # The status endpoint reports failure and the UI offers retry.
        request.app.state.vision_warmup_task = asyncio.create_task(initialize())
    return {'cv_engine': 'loading', 'message': 'Loading face model. The first download may take several minutes.'}


@router.get('/exceptions')
async def get_exceptions(_: dict = Depends(require_user)):
    """Get manual exceptions log."""
    from app.database import get_connection

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM admin_actions ORDER BY created_at DESC')
    exceptions = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return {'exceptions': exceptions}


@router.post('/exceptions')
async def log_exception(exc: ExceptionLog, _: None = Depends(require_admin)):
    """Log a manual exception."""
    from app.database import get_connection

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO admin_actions (action, target_user_id, reason)
        VALUES (?, ?, ?)
    ''', (exc.action, exc.target_user_id, exc.reason))

    conn.commit()
    conn.close()

    return {'success': True}


@router.post('/payment-update')
async def update_payment(update: PaymentUpdate, _: None = Depends(require_admin)):
    """Update payment status (logs admin action)."""
    from app.database import get_connection

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE users SET payment_status = ?, updated_at = CURRENT_TIMESTAMP
        WHERE user_id = ?
    ''', (update.payment_status, update.user_id))

    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail='User not found')

    cursor.execute('''
        INSERT INTO admin_actions (action, target_user_id, reason)
        VALUES (?, ?, ?)
    ''', ('Payment status update', update.user_id,
          f'Changed to {update.payment_status}'))

    conn.commit()
    conn.close()

    return {'success': True}
