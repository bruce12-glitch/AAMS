"""
Users API Routes for FacePass FabLab.
Implements CRUD for users plus image-based enrollment (§17).

Enrollment: POST /api/users/enroll
  - JSON body: user details + images (base64 list, 3-10 shots)
  - Server decodes each image, quality-checks, extracts ArcFace embeddings,
    stores the best 3, saves evidence photos, issues a signed QR token.
  - Requires X-Admin-Token when API_ADMIN_PASSWORD is configured.

Webcam CLI enrollment remains available: python -m enrollment.enroll_user
"""

import base64
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.security import require_admin

logger = logging.getLogger(__name__)
router = APIRouter(prefix='/api/users', tags=['users'])


class UserCreate(BaseModel):
    user_id: str
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    user_type: str = 'student'
    payment_status: str = 'inactive'
    payment_expiry: Optional[str] = None


class EnrollRequest(UserCreate):
    consent_given: bool = False
    images: List[str] = []          # base64 / data-URI face photos


@router.get('')
async def list_users():
    """List all users."""
    from app.database import get_connection

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users ORDER BY created_at DESC')
    users = [dict(row) for row in cursor.fetchall()]
    conn.close()

    # Never ship binary embeddings to the client
    for user in users:
        user['face_embedding'] = None
        user['face_embedding_2'] = None
        user['face_embedding_3'] = None
        user['enrolled'] = any(
            user.get(k) for k in ('face_embedding', 'face_embedding_2', 'face_embedding_3')
        ) or False

    return {'users': users}


@router.post('/enroll')
async def enroll_user(req: EnrollRequest, _: None = Depends(require_admin)):
    """
    Full enrollment (§17): store profile + compute real face embeddings
    from uploaded images + generate signed QR token. Idempotent per user_id
    (re-enrollment overwrites embeddings).
    """
    import numpy as np

    from app.database import get_connection
    from app.qr_manager import QRManager
    from app.utils import save_frame
    from app.vision import VisionUnavailableError, analyze_frame, decode_image

    if not req.consent_given:
        raise HTTPException(status_code=400,
                            detail='Consent is required before biometric enrollment (§26)')
    if not req.images:
        raise HTTPException(status_code=400,
                            detail='At least one face image is required')

    try:
        frames = [decode_image(img) for img in req.images]
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # ---- CV: quality-check + embed each frame ------------------------ #
    try:
        passes = []  # list of (source_frame, analysis)
        for idx, frame in enumerate(frames):
            analysis = analyze_frame(frame)
            if analysis['face_count'] == 0:
                continue
            if not analysis['quality_passed']:
                logger.info('Enroll img %d rejected: %s', idx,
                            '; '.join(analysis['quality_reasons']))
                continue
            passes.append((frame, analysis))
    except VisionUnavailableError as exc:
        raise HTTPException(status_code=503, detail=f'CV engine unavailable: {exc}')

    if len(passes) < 1:
        raise HTTPException(status_code=422, detail=(
            'No usable face found in the provided images. Ensure a clear, '
            'well-lit, front-facing photo (>120px face width).'))

    # ---- Pick best 3 embeddings (§17.4) ------------------------------ #
    picked = passes[:3]
    embeddings = [a['embedding'].astype(np.float64) for _, a in picked]

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('SELECT id FROM users WHERE user_id = ?', (req.user_id,))
        exists = cursor.fetchone()

        emb_bytes = [e.tobytes() for e in embeddings]
        emb_bytes += [None] * (3 - len(emb_bytes))

        # Save the first passing frame as the profile photo
        photo_rel = save_frame(picked[0][0], 'enrolled', prefix=req.user_id)

        if exists:
            cursor.execute('''
                UPDATE users SET name=?, phone=?, email=?, user_type=?,
                    payment_status=?, payment_expiry=?,
                    face_embedding=?, face_embedding_2=?, face_embedding_3=?,
                    face_image_path=?, consent_given=?, active=1,
                    updated_at=CURRENT_TIMESTAMP
                WHERE user_id=?
            ''', (req.name, req.phone, req.email, req.user_type,
                  req.payment_status, req.payment_expiry,
                  emb_bytes[0], emb_bytes[1], emb_bytes[2],
                  photo_rel, int(req.consent_given), req.user_id))
        else:
            cursor.execute('''
                INSERT INTO users (user_id, name, phone, email, user_type,
                    payment_status, payment_expiry, face_embedding,
                    face_embedding_2, face_embedding_3, face_image_path,
                    consent_given, active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            ''', (req.user_id, req.name, req.phone, req.email, req.user_type,
                  req.payment_status, req.payment_expiry,
                  emb_bytes[0], emb_bytes[1], emb_bytes[2],
                  photo_rel, int(req.consent_given)))

        # Issue active token (replace old ones)
        qr = QRManager()
        token = qr.generate_token(req.user_id)
        cursor.execute('UPDATE tokens SET active = 0 WHERE user_id = ?',
                       (req.user_id,))
        cursor.execute('''
            INSERT INTO tokens (token_value, user_id, token_type, active)
            VALUES (?, ?, 'qr', 1)
        ''', (req.user_id, req.user_id))

        conn.commit()
    except Exception as exc:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    finally:
        conn.close()

    return {
        'success': True,
        'user_id': req.user_id,
        'embeddings_stored': len(embeddings),
        'images_rejected': len(req.images) - len(passes),
        'token': token,
        'qr_data_uri': f'data:image/png;base64,' +
                       base64.b64encode(qr.generate_qr_image(req.user_id)).decode(),
    }


@router.post('')
async def create_user(user: UserCreate, _: None = Depends(require_admin)):
    """Add user record only (no biometrics)."""
    from app.database import get_connection

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO users (user_id, name, phone, email, user_type,
                               payment_status, payment_expiry)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user.user_id, user.name, user.phone, user.email, user.user_type,
              user.payment_status, user.payment_expiry))
        conn.commit()
        return {'success': True, 'user_id': user.user_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()


@router.put('/{user_id}')
async def update_user(user_id: str, payment_status: Optional[str] = None,
                      active: Optional[int] = None,
                      _: None = Depends(require_admin)):
    """Update user (payment, active status)."""
    from app.database import get_connection

    conn = get_connection()
    cursor = conn.cursor()

    updates, params = [], []
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
        UPDATE users SET {", ".join(updates)}, updated_at = CURRENT_TIMESTAMP
        WHERE user_id = ?
    ''', params)

    conn.commit()
    affected = cursor.rowcount
    conn.close()

    if affected == 0:
        raise HTTPException(status_code=404, detail='User not found')
    return {'success': True}


@router.delete('/{user_id}')
async def delete_user(user_id: str, _: None = Depends(require_admin)):
    """Delete user + purge embeddings (§26 data-protection right)."""
    from app.database import get_connection

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM tokens WHERE user_id = ?', (user_id,))
    cursor.execute('DELETE FROM occupants WHERE user_id = ?', (user_id,))
    cursor.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
    conn.commit()
    affected = cursor.rowcount
    conn.close()

    if affected == 0:
        raise HTTPException(status_code=404, detail='User not found')
    return {'success': True}


@router.post('/{user_id}/tokens/revoke')
async def revoke_and_reissue_token(user_id: str, _: None = Depends(require_admin)):
    """
    Lost-token flow (§30.4): deactivate every active token for the user
    and issue a fresh signed QR pass. Old passes stop working immediately.
    """
    import base64 as b64

    from app.database import get_connection
    from app.qr_manager import QRManager

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM users WHERE user_id = ?', (user_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail='User not found')

    qr = QRManager()
    token = qr.generate_token(user_id)

    cursor.execute('UPDATE tokens SET active = 0 WHERE user_id = ?', (user_id,))
    cursor.execute('''
        INSERT INTO tokens (token_value, user_id, token_type, active)
        VALUES (?, ?, 'qr', 1)
    ''', (user_id, user_id))
    conn.commit()
    conn.close()

    return {
        'success': True,
        'user_id': user_id,
        'token': token,
        'qr_data_uri': 'data:image/png;base64,' +
                       b64.b64encode(qr.generate_qr_image(user_id)).decode(),
    }


@router.get('/{user_id}/export')
async def export_user_data(user_id: str, _: None = Depends(require_admin)):
    """
    Data-portability export (DPDP access right): everything stored about
    one person, with biometric blobs stripped (they are not portable).
    """
    from app.database import get_connection

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail='User not found')
    profile = dict(row)
    profile['face_embedding'] = '[biometric vector withheld]'
    profile['face_embedding_2'] = '[biometric vector withheld]'
    profile['face_embedding_3'] = '[biometric vector withheld]'

    cursor.execute(
        'SELECT event_time, decision, reason, tag, similarity FROM entry_logs '
        'WHERE claimed_id = ? OR recognized_id = ? ORDER BY id DESC',
        (user_id, user_id))
    entries = [dict(r) for r in cursor.fetchall()]

    cursor.execute(
        'SELECT entry_time, exit_time, status FROM occupants WHERE user_id = ? '
        'ORDER BY id DESC', (user_id,))
    occupancy = [dict(r) for r in cursor.fetchall()]
    conn.close()

    return {'profile': profile, 'entry_logs': entries,
            'occupancy_history': occupancy}


@router.get('/{user_id}/qr')
async def generate_qr(user_id: str):
    """Generate signed QR pass for user."""
    from app.qr_manager import QRManager

    qr_manager = QRManager()
    qr_bytes = qr_manager.generate_qr_image(user_id)
    qr_base64 = base64.b64encode(qr_bytes).decode()
    return {'qr_data_uri': f'data:image/png;base64,{qr_base64}'}
