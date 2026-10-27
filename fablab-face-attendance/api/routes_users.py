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

import asyncio
import base64
import logging
import sqlite3
from typing import List, Optional, Literal

from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel, Field, ConfigDict, field_validator

from app.security import require_admin, require_user, validate_user_id

logger = logging.getLogger(__name__)
router = APIRouter(prefix='/api/users', tags=['users'])


class UserCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')
    user_id: str
    name: str = Field(min_length=1, max_length=120)
    phone: Optional[str] = Field(default=None, max_length=30)
    email: Optional[str] = Field(default=None, max_length=254)
    user_type: Literal['student', 'faculty', 'staff', 'guest'] = 'student'
    payment_status: Literal['active', 'pending', 'expired', 'inactive'] = 'inactive'
    payment_expiry: Optional[str] = None
    password: Optional[str] = None  # compatibility with old records
    department: Optional[str] = Field(default=None, max_length=120)
    year: Optional[int] = Field(default=None, ge=1, le=6)
    section: Optional[str] = Field(default=None, max_length=30)

    @field_validator('payment_expiry')
    @classmethod
    def validate_expiry(cls, value):
        if value:
            from datetime import date
            date.fromisoformat(value)
        return value or None



class EnrollRequest(UserCreate):
    consent_given: bool = False
    images: List[str] = Field(default_factory=list, max_length=10)  # base64 / data-URI face photos


def _require_valid_user_id(user_id: str) -> str:
    """Reject IDs that are not plain identifiers (file-name safety, clarity)."""
    try:
        return validate_user_id(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


def _check_email_available(email, user_id):
    if not email:
        raise HTTPException(status_code=400, detail='SRMIST email is required')
    from app.database import get_connection
    conn = get_connection()
    try:
        row = conn.execute('SELECT user_id FROM users WHERE lower(email)=lower(?) AND user_id<>?', (email, user_id)).fetchone()
        if row:
            raise HTTPException(status_code=409, detail='This email is already assigned to another student')
    finally:
        conn.close()


async def _notify_student(user_id, name, action):
    from app.config import get_telegram_config
    from app.alerts import AlertService
    if get_telegram_config().get('notify_on_enrollment', True):
        try:
            await AlertService().queue_and_deliver('ENROLLMENT', f'AAMS — {action}\nName: {name}\nStudent ID: {user_id}')
        except Exception as exc:
            logger.warning('Student notification failed (%s)', type(exc).__name__)


class UserUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    phone: Optional[str] = Field(default=None, max_length=30)
    email: Optional[str] = Field(default=None, max_length=254)
    user_type: Optional[Literal['student', 'faculty', 'staff', 'guest']] = None
    department: Optional[str] = Field(default=None, max_length=120)
    year: Optional[int] = Field(default=None, ge=1, le=6)
    section: Optional[str] = Field(default=None, max_length=30)
    payment_status: Optional[Literal['active', 'pending', 'expired', 'inactive']] = None
    payment_expiry: Optional[str] = None
    active: Optional[Literal[0, 1]] = None

    _expiry = field_validator('payment_expiry')(UserCreate.validate_expiry.__func__)


@router.get('')
async def list_users(_: dict = Depends(require_user)):
    """List all users."""
    from app.database import get_connection

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users ORDER BY created_at DESC')
    users = [dict(row) for row in cursor.fetchall()]
    conn.close()

    # Biometrics and credentials never leave the server. `enrolled` must be
    # derived BEFORE the embeddings are blanked, or every member would look
    # face-less in the console.
    for user in users:
        user['enrolled'] = any(
            user.get(k) for k in ('face_embedding', 'face_embedding_2', 'face_embedding_3')
        )
        user['face_embedding'] = None
        user['face_embedding_2'] = None
        user['face_embedding_3'] = None
        user['password_hash'] = None

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

    req.user_id = _require_valid_user_id(req.user_id)

    # SRMIST-only rule: no other mail domain is evaluated or enrolled.
    if req.email:
        from app.auth import reject_non_srmist
        try:
            req.email = reject_non_srmist(req.email)
        except ValueError as exc:
            raise HTTPException(status_code=403, detail=str(exc))

    # The showcase uses a shared password supplied through the environment.
    # Keep the legacy per-member hash optional for database compatibility.
    from app.auth import hash_password
    _check_email_available(req.email, req.user_id)
    pwd_hash = None
    if req.password:
        try:
            pwd_hash = hash_password(req.password)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

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
    def analyze_enrollment_frames():
        passes = []  # list of (source_frame, analysis)
        rejections = []
        for idx, frame in enumerate(frames):
            analysis = analyze_frame(frame)
            if analysis['face_count'] == 0:
                rejections.append(f'photo {idx + 1}: no face detected')
                continue
            if analysis['face_count'] != 1:
                rejections.append(f'photo {idx + 1}: keep only one face in the photo')
                continue
            if not analysis['quality_passed']:
                reasons = analysis['quality_reasons'] or ['quality check failed']
                logger.info('Enroll img %d rejected: %s', idx,
                            '; '.join(reasons))
                rejections.append(
                    f"photo {idx + 1}: {'; '.join(reasons)}")
                continue
            passes.append((frame, analysis))
        return passes, rejections

    try:
        # InsightFace inference is CPU-bound. Keep all frames sequential on a
        # single worker (the model session is shared) while leaving FastAPI's
        # event loop free to serve health, dashboard and Telegram requests.
        passes, rejections = await asyncio.to_thread(analyze_enrollment_frames)
    except VisionUnavailableError as exc:
        raise HTTPException(status_code=503, detail=f'CV engine unavailable: {exc}')

    if len(passes) < 1:
        reason_text = '; '.join(rejections[:3])
        raise HTTPException(status_code=422, detail=(
            'No usable face found in the provided images. Ensure a clear, '
            'well-lit, front-facing photo (>120px face width). '
            f'Rejected because: {reason_text}'))

    # ---- Pick best 3 embeddings (§17.4) ------------------------------ #
    # Do not put different people's faces under one member. Checking every
    # pair prevents a mixed enrollment from granting either person's entry.
    from app.face_engine import FaceEngine
    from app.config import get_face_config
    threshold = float(get_face_config().get('match_threshold', 0.45))
    for index, (_, analysis) in enumerate(passes):
        for _, other in passes[index + 1:]:
            if FaceEngine.match_embeddings(analysis['embedding'], other['embedding']) < threshold:
                raise HTTPException(status_code=422, detail='Enrollment photos do not consistently match the same person. Retake clear original photos of one member, using the same webcam.')
    picked = sorted(passes, key=lambda item: item[1].get('quality_metrics', {}).get('blur_variance', 0), reverse=True)[:3]
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
                    face_image_path=?, password_hash=?, consent_given=?,
                    active=1, updated_at=CURRENT_TIMESTAMP
                WHERE user_id=?
            ''', (req.name, req.phone, req.email, req.user_type,
                  req.payment_status, req.payment_expiry,
                  emb_bytes[0], emb_bytes[1], emb_bytes[2],
                  photo_rel, pwd_hash, int(req.consent_given), req.user_id))
        else:
            cursor.execute('''
                INSERT INTO users (user_id, name, phone, email, user_type,
                    payment_status, payment_expiry, face_embedding,
                    face_embedding_2, face_embedding_3, face_image_path,
                    password_hash, consent_given, active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            ''', (req.user_id, req.name, req.phone, req.email, req.user_type,
                  req.payment_status, req.payment_expiry,
                  emb_bytes[0], emb_bytes[1], emb_bytes[2],
                  photo_rel, pwd_hash, int(req.consent_given)))

        cursor.execute('UPDATE users SET department=?, year=?, section=? WHERE user_id=?',
                       (req.department, req.year, req.section, req.user_id))

        # Issue active token (replace old ones).
        #
        # tokens.token_value is UNIQUE. This endpoint is documented as
        # idempotent — re-enrolling must overwrite — but deactivating the old
        # row with `active = 0` left it occupying the unique value, so a second
        # enrollment for the same user died with
        #   "UNIQUE constraint failed: tokens.token_value"  (HTTP 400).
        # Delete the superseded rows instead of only deactivating them.
        qr = QRManager()
        token = qr.generate_token(req.user_id)
        token_value = qr.serialize_token(token)
        cursor.execute('DELETE FROM tokens WHERE user_id = ?', (req.user_id,))
        cursor.execute('''
            INSERT INTO tokens (token_value, user_id, token_type, active)
            VALUES (?, ?, 'qr', 1)
        ''', (token_value, req.user_id))

        conn.commit()
    except Exception as exc:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    finally:
        conn.close()

    await _notify_student(req.user_id, req.name, 'Face enrollment completed')
    return {
        'success': True,
        'user_id': req.user_id,
        'embeddings_stored': len(embeddings),
        'images_rejected': len(req.images) - len(passes),
        'token': token,
        'qr_data_uri': f'data:image/png;base64,' +
                       base64.b64encode(qr.generate_qr_image(
                           req.user_id, token=token)).decode(),
    }


@router.post('')
async def create_user(user: UserCreate, _: None = Depends(require_admin)):
    """Add user record only (no biometrics). SRMIST mail only."""
    user.user_id = _require_valid_user_id(user.user_id)
    if user.email:
        from app.auth import reject_non_srmist
        try:
            user.email = reject_non_srmist(user.email)
        except ValueError as exc:
            raise HTTPException(status_code=403, detail=str(exc))
    _check_email_available(user.email, user.user_id)
    pwd_hash = None
    if user.password:
        from app.auth import hash_password
        try:
            pwd_hash = hash_password(user.password)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
    from app.database import get_connection

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO users (user_id, name, phone, email, user_type,
                               payment_status, payment_expiry, password_hash, department, year, section)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user.user_id, user.name, user.phone, user.email, user.user_type,
              user.payment_status, user.payment_expiry, pwd_hash, user.department, user.year, user.section))
        conn.commit()
        await _notify_student(user.user_id, user.name, 'Student added')
        return {'success': True, 'user_id': user.user_id}
    except sqlite3.IntegrityError:
        conn.rollback()
        raise HTTPException(status_code=409, detail='This student ID or email is already registered') from None
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()


class PasswordReset(BaseModel):
    password: str = ''


@router.post('/{user_id}/password')
async def reset_password(user_id: str, req: PasswordReset,
                         _: None = Depends(require_admin)):
    """Set or reset a member's console password (admin only)."""
    from app.auth import hash_password
    try:
        pwd_hash = hash_password(req.password or '')
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    from app.database import get_connection
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE users SET password_hash=?, updated_at=CURRENT_TIMESTAMP
        WHERE user_id=?
    ''', (pwd_hash, user_id))
    conn.commit()
    affected = cursor.rowcount
    conn.close()

    if affected == 0:
        raise HTTPException(status_code=404, detail='User not found')
    return {'success': True}


@router.put('/{user_id}')
async def update_user(user_id: str, payment_status: Optional[Literal['active', 'pending', 'expired', 'inactive']] = None,
                      active: Optional[Literal[0, 1]] = None,
                      profile: Optional[UserUpdate] = Body(default=None),
                      _: dict = Depends(require_admin)):
    """Edit student details; retain legacy payment query support."""
    from app.database import get_connection
    values = profile.model_dump(exclude_unset=True) if profile else {}
    if payment_status is not None:
        values['payment_status'] = payment_status
    if active is not None:
        values['active'] = active
    if not values:
        raise HTTPException(status_code=400, detail='No fields to update')
    for required in ('name', 'email', 'user_type', 'payment_status', 'active'):
        if required in values and values[required] is None:
            raise HTTPException(status_code=400, detail=f'{required} cannot be empty')
    if 'email' in values:
        from app.auth import reject_non_srmist
        try:
            values['email'] = reject_non_srmist(values['email'])
        except ValueError as exc:
            raise HTTPException(status_code=403, detail=str(exc))
        _check_email_available(values['email'], user_id)
    conn = get_connection()
    try:
        assignments = ', '.join(f'{key}=?' for key in values)
        cursor = conn.execute(f'UPDATE users SET {assignments}, updated_at=CURRENT_TIMESTAMP WHERE user_id=?', (*values.values(), user_id))
        if not cursor.rowcount:
            raise HTTPException(status_code=404, detail='Student not found')
        if values.get('active') == 0:
            conn.execute('UPDATE tokens SET active=0 WHERE user_id=?', (user_id,))
            conn.execute("UPDATE occupants SET status='exited', exit_time=CURRENT_TIMESTAMP WHERE user_id=? AND status='inside'", (user_id,))
        conn.commit()
    finally:
        conn.close()
    return {'success': True}


@router.delete('/{user_id}')
async def delete_user(user_id: str, _: None = Depends(require_admin)):
    """Delete user + purge embeddings (§26 data-protection right)."""
    from app.database import get_connection

    conn = get_connection()
    cursor = conn.cursor()
    row = cursor.execute('SELECT face_image_path FROM users WHERE user_id=?', (user_id,)).fetchone()
    cursor.execute('DELETE FROM tokens WHERE user_id = ?', (user_id,))
    cursor.execute('DELETE FROM occupants WHERE user_id = ?', (user_id,))
    cursor.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
    conn.commit()
    affected = cursor.rowcount
    conn.close()

    if affected == 0:
        raise HTTPException(status_code=404, detail='User not found')
    if row and row['face_image_path']:
        from app.config import BASE_DIR
        from pathlib import Path
        image = (BASE_DIR / row['face_image_path']).resolve()
        if image.is_relative_to((BASE_DIR / 'images' / 'enrolled').resolve()):
            image.unlink(missing_ok=True)
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
    token_value = qr.serialize_token(token)

    # Same UNIQUE-constraint issue as enrollment: deactivating the old row
    # still left it holding the unique token_value, so a second re-key for the
    # same user failed permanently. Remove superseded rows first.
    cursor.execute('DELETE FROM tokens WHERE user_id = ?', (user_id,))
    cursor.execute('''
        INSERT INTO tokens (token_value, user_id, token_type, active)
        VALUES (?, ?, 'qr', 1)
    ''', (token_value, user_id))
    conn.commit()
    conn.close()

    return {
        'success': True,
        'user_id': user_id,
        'token': token,
        'qr_data_uri': 'data:image/png;base64,' +
                       b64.b64encode(qr.generate_qr_image(
                           user_id, token=token)).decode(),
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
    profile['password_hash'] = '[credential withheld]'

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
async def generate_qr(user_id: str, _: None = Depends(require_admin)):
    """
    Generate signed QR pass for user.

    Admin only: the QR is a bearer credential for door entry, so an open
    endpoint here would hand anyone a working pass for any member.
    """
    from app.qr_manager import QRManager

    from app.database import get_connection

    qr_manager = QRManager()
    conn = get_connection()
    row = conn.execute(
        "SELECT token_value FROM tokens WHERE user_id=? AND active=1 "
        "ORDER BY id DESC LIMIT 1", (user_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail='No active QR pass for this member')
    verdict = qr_manager.verify_token(row['token_value'])
    if not verdict.get('valid'):
        raise HTTPException(status_code=410, detail='QR pass expired — re-key this member')
    qr_bytes = qr_manager.generate_qr_image(user_id, token=verdict['token'])
    qr_base64 = base64.b64encode(qr_bytes).decode()
    return {'qr_data_uri': f'data:image/png;base64,{qr_base64}'}
