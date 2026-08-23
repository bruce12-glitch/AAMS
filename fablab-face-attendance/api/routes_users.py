"""
Users API Routes for FacePass FabLab.
Implements CRUD for users/enrollment.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix='/api/users', tags=['users'])

class UserCreate(BaseModel):
    user_id: str
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    user_type: str = 'student'
    payment_status: str = 'inactive'
    payment_expiry: Optional[str] = None

@router.get('')
async def list_users():
    """List all users."""
    from app.database import get_connection
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users ORDER BY created_at DESC')
    users = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    # Convert embeddings to None (don't send binary data)
    for user in users:
        user['face_embedding'] = None
        user['face_embedding_2'] = None
        user['face_embedding_3'] = None
    
    return {'users': users}

@router.post('')
async def create_user(user: UserCreate):
    """Add new user (enrollment)."""
    from app.database import get_connection
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO users (user_id, name, phone, email, user_type, payment_status, payment_expiry)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user.user_id, user.name, user.phone, user.email, user.user_type, user.payment_status, user.payment_expiry))
        
        conn.commit()
        return {'success': True, 'user_id': user.user_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()

@router.put('/{user_id}')
async def update_user(user_id: str, payment_status: Optional[str] = None, active: Optional[int] = None):
    """Update user (payment, active status)."""
    from app.database import get_connection
    
    conn = get_connection()
    cursor = conn.cursor()
    
    updates = []
    params = []
    
    if payment_status is not None:
        updates.append('payment_status = ?')
        params.append(payment_status)
    
    if active is not None:
        updates.append('active = ?')
        params.append(active)
    
    if not updates:
        raise HTTPException(status_code=400, detail='No fields to update')
    
    params.append(user_id)
    
    cursor.execute(f'''
        UPDATE users SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP
        WHERE user_id = ?
    ''', params)
    
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    
    if affected == 0:
        raise HTTPException(status_code=404, detail='User not found')
    
    return {'success': True}

@router.delete('/{user_id}')
async def delete_user(user_id: str):
    """Delete user + purge embeddings."""
    from app.database import get_connection
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    
    if affected == 0:
        raise HTTPException(status_code=404, detail='User not found')
    
    return {'success': True}

@router.get('/{user_id}/qr')
async def generate_qr(user_id: str):
    """Generate signed QR pass for user."""
    from app.qr_manager import QRManager
    import base64
    
    qr_manager = QRManager()
    qr_bytes = qr_manager.generate_qr_image(user_id)
    
    # Return as base64 for frontend display
    qr_base64 = base64.b64encode(qr_bytes).decode()
    
    return {'qr_data_uri': f'data:image/png;base64,{qr_base64}'}
