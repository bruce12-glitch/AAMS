"""
Admin API Routes for FacePass FabLab.
Implements admin actions, exceptions log.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix='/api/admin', tags=['admin'])

class ExceptionLog(BaseModel):
    action: str
    target_user_id: str
    reason: str

class PaymentUpdate(BaseModel):
    user_id: str
    payment_status: str

@router.get('/exceptions')
async def get_exceptions():
    """Get manual exceptions log."""
    from app.database import get_connection
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM admin_actions ORDER BY created_at DESC')
    exceptions = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return {'exceptions': exceptions}

@router.post('/exceptions')
async def log_exception(exc: ExceptionLog):
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
async def update_payment(update: PaymentUpdate):
    """Update payment status (logs admin action)."""
    from app.database import get_connection
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Update user
    cursor.execute('''
        UPDATE users SET payment_status = ?, updated_at = CURRENT_TIMESTAMP
        WHERE user_id = ?
    ''', (update.payment_status, update.user_id))
    
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail='User not found')
    
    # Log admin action
    cursor.execute('''
        INSERT INTO admin_actions (action, target_user_id, reason)
        VALUES (?, ?, ?)
    ''', ('Payment status update', update.user_id, f'Changed to {update.payment_status}'))
    
    conn.commit()
    conn.close()
    
    return {'success': True}
