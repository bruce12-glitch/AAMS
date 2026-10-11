"""
Auth API — SRMIST email + the shared AAMS access password.

POST /api/auth/login
  body: { "email": "name@srmist.edu.in", "password": "..." }
  - 200 + { ok, email, name, user_id } when the email uses the exact
    SRMIST domain and the shared password verifies.
  - 400 when email or password is missing.
  - 403 for any other domain or password.

Brute force: one mail ID gets LOGIN_RATE_LIMIT attempts per minute
(default 10) and its whole IP five times that, so a shared campus NAT
survives one account being probed. The global per-IP limiter stays as a
second, much wider net.
"""

import os

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.auth import (
    SRMIST_DOMAIN,
    MIN_PASSWORD_LEN,
    access_password_configured,
    is_srmist_email,
    normalize_email,
    verify_access_password,
)
from app.security import (
    admin_email,
    auth_enabled,
    issue_session,
    require_user,
    session_security_ready,
)

router = APIRouter(prefix='/api/auth', tags=['auth'])

WINDOW_SECONDS = 60
# One mail ID gets LOGIN_RATE_LIMIT tries; its whole IP gets five times that,
# so a shared campus NAT is never locked out by a single noisy account.
IP_ATTEMPTS_FACTOR = 5


def login_attempt_limit() -> int:
    try:
        return max(1, int(os.getenv('LOGIN_RATE_LIMIT', '10')))
    except ValueError:
        return 10


class LoginRequest(BaseModel):
    email: str = ''
    password: str = ''


def _check_login_rate(request: Request, email: str) -> None:
    """429 once an IP or a mail ID burns its attempts for this minute."""
    from app.ratelimit import get_backend

    backend = get_backend()
    limit = login_attempt_limit()
    ip = request.client.host if request.client else 'unknown'

    # Tighter key first: when both are close to full, the message should
    # blame the mail ID being guessed rather than the shared network.
    keys = [('login:mail:' + email.lower(), limit)] if email else []
    keys.append(('login:ip:' + ip, limit * IP_ATTEMPTS_FACTOR))

    for key, cap in keys:
        if not backend.allow(key, cap, WINDOW_SECONDS):
            raise HTTPException(
                status_code=429,
                detail='Too many sign-in attempts — wait a minute and try again',
                headers={'Retry-After': str(backend.retry_after(key, WINDOW_SECONDS))},
            )


@router.post('/login')
async def login(req: LoginRequest, request: Request):
    email = normalize_email(req.email)
    if not email:
        raise HTTPException(
            status_code=400,
            detail='SRMIST email is required (e.g. name@srmist.edu.in)',
        )
    # Rate limit before touching the database, so junk traffic costs a
    # counter entry and nothing else.
    _check_login_rate(request, email)
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

    if not access_password_configured():
        raise HTTPException(
            status_code=503,
            detail='AAMS access password is not configured on the server',
        )

    if auth_enabled() and not session_security_ready():
        raise HTTPException(
            status_code=503,
            detail='Server session security is not configured',
        )

    if not verify_access_password(req.password):
        raise HTTPException(status_code=403, detail='Wrong email or password')

    # The configured administrator mail receives the admin role. Every other
    # valid SRMIST address receives a member session. This keeps mutation
    # privileges least-privileged even though the showcase password is shared.
    if email == admin_email():
        session = issue_session(
            email=email, user_id='ADMIN', name='Fab Lab Administrator', role='admin')
        return {'ok': True, 'domain': SRMIST_DOMAIN, **session}

    from app.database import get_connection

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT user_id, name, email, password_hash, active FROM users '
        'WHERE lower(email) = ?',
        (email,))
    row = cursor.fetchone()
    conn.close()

    session = issue_session(
        email=email,
        user_id=row['user_id'] if row and row['active'] else email.split('@', 1)[0],
        name=row['name'] if row and row['active'] else email.split('@', 1)[0],
        role='member',
    )
    return {
        'ok': True,
        'domain': SRMIST_DOMAIN,
        **session,
    }


@router.get('/session')
async def session_info(session: dict = Depends(require_user)):
    """Validate a stored browser session and return its safe identity fields."""
    return {k: session[k] for k in ('email', 'name', 'user_id', 'role', 'exp')}


@router.get('/policy')
async def auth_policy():
    """Lets the frontend render the rule without hardcoding it twice."""
    return {
        'domain': SRMIST_DOMAIN,
        'suffix': '@' + SRMIST_DOMAIN,
        'min_password_len': MIN_PASSWORD_LEN,
        'shared_password_required': True,
        'shared_password_configured': access_password_configured(),
    }
