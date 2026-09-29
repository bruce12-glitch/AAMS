"""
Auth API — SRMIST email + member password.

POST /api/auth/login
  body: { "email": "name@srmist.edu.in", "password": "..." }
  - 200 + { ok, email, name, user_id } when the mail belongs to an
    enrolled member and the password verifies.
  - 400 when email or password is missing.
  - 403 for anything else: non-SRMIST domain, unknown mail, missing
    password on the account, or wrong password. Messages stay specific
    enough for a lab operator to act on.

Passwords are set at enrollment (Members → ＋ Enroll) or via the admin
password-reset endpoint; only PBKDF2 hashes are stored, never plain text.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.auth import (
    SRMIST_DOMAIN,
    MIN_PASSWORD_LEN,
    is_srmist_email,
    normalize_email,
    verify_password,
)

router = APIRouter(prefix='/api/auth', tags=['auth'])


class LoginRequest(BaseModel):
    email: str = ''
    password: str = ''


@router.post('/login')
async def login(req: LoginRequest):
    email = normalize_email(req.email)
    if not email:
        raise HTTPException(
            status_code=400,
            detail='SRMIST email is required (e.g. name@srmist.edu.in)',
        )
    if not is_srmist_email(email):
        raise HTTPException(
            status_code=403,
            detail=f'Only @{SRMIST_DOMAIN} mail IDs are allowed',
        )
    if not req.password:
        raise HTTPException(
            status_code=400,
            detail='Password is required',
        )

    from app.database import get_connection

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT user_id, name, email, password_hash, active FROM users '
        'WHERE lower(email) = ?',
        (email,))
    row = cursor.fetchone()
    conn.close()

    if not row or not row['active']:
        raise HTTPException(
            status_code=403,
            detail='This mail ID is not enrolled — contact the Fab Lab admin',
        )
    if not row['password_hash']:
        raise HTTPException(
            status_code=403,
            detail='No password set for this account — ask the admin to reset it',
        )
    if not verify_password(req.password, row['password_hash']):
        raise HTTPException(
            status_code=403,
            detail='Wrong password for this mail ID',
        )

    return {
        'ok': True,
        'email': email,
        'name': row['name'],
        'user_id': row['user_id'],
        'domain': SRMIST_DOMAIN,
    }


@router.get('/policy')
async def auth_policy():
    """Lets the frontend render the rule without hardcoding it twice."""
    return {
        'domain': SRMIST_DOMAIN,
        'suffix': '@' + SRMIST_DOMAIN,
        'min_password_len': MIN_PASSWORD_LEN,
    }
