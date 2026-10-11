"""
Security helpers for FacePass FabLab (§27.2 API Security).

Admin protection: mutating endpoints require header
    X-Admin-Token: <API_ADMIN_PASSWORD from .env>

If no password is configured (placeholder/empty) the guard runs in
dev-open mode and logs a warning — convenient locally, loud in logs.
"""

import base64
import hashlib
import hmac
import json
import logging
import os
import re
import time
from pathlib import Path

from fastapi import HTTPException, Request

from app.config import get_security_config, BASE_DIR

logger = logging.getLogger(__name__)

_PLACEHOLDERS = {"", "CHANGE_THIS", "your_admin_password_here"}

# Member IDs become file names (evidence photos) and SQL parameters. SQL is
# parameterised, but the file name is not: '../x' would escape images/.
_USER_ID_RE = re.compile(r'^[A-Za-z0-9._-]{1,64}$')


def validate_user_id(user_id: str) -> str:
    """Return the ID if it is a plain identifier, else raise ValueError."""
    value = (user_id or '').strip()
    if not _USER_ID_RE.match(value):
        raise ValueError(
            'user_id must be 1-64 characters of letters, digits, dot, '
            'dash or underscore (no spaces or slashes)'
        )
    return value


def admin_password() -> str:
    try:
        return (get_security_config().get('api_admin_password') or '').strip()
    except Exception:
        return ''


def auth_enabled() -> bool:
    return admin_password() not in _PLACEHOLDERS


def admin_email() -> str:
    """Email used for the browser administrator account."""
    return os.getenv('ADMIN_EMAIL', 'admin@srmist.edu.in').strip().lower()


def _session_secret() -> str:
    """Return the HMAC secret used for short-lived browser sessions."""
    explicit = os.getenv('SESSION_SECRET_KEY', '').strip()
    if explicit:
        return explicit
    try:
        return str(get_security_config().get('qr_secret_key') or '').strip()
    except Exception:
        return ''


def session_security_ready() -> bool:
    secret = _session_secret()
    return bool(secret) and secret not in _PLACEHOLDERS and not secret.startswith('CHANGE_')


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b'=').decode('ascii')


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + '=' * (-len(value) % 4))


def issue_session(*, email: str, user_id: str, name: str, role: str = 'member') -> dict:
    """Issue a compact, signed, expiring browser session."""
    try:
        ttl = max(300, int(os.getenv('SESSION_TTL_SECONDS', '28800')))
    except ValueError:
        ttl = 28800
    now = int(time.time())
    payload = {
        'email': email,
        'user_id': user_id,
        'name': name,
        'role': role,
        'iat': now,
        'exp': now + ttl,
    }
    encoded = _b64encode(json.dumps(payload, separators=(',', ':'), sort_keys=True).encode())
    signature = hmac.new(_session_secret().encode(), encoded.encode(), hashlib.sha256).digest()
    return {
        **payload,
        'token': encoded + '.' + _b64encode(signature),
        'expires_at': payload['exp'],
    }


def verify_session(token: str) -> dict:
    """Verify a browser session signature and expiry; raise 401 on failure."""
    try:
        encoded, supplied = token.split('.', 1)
        expected = hmac.new(
            _session_secret().encode(), encoded.encode(), hashlib.sha256
        ).digest()
        if not hmac.compare_digest(_b64decode(supplied), expected):
            raise ValueError('signature')
        payload = json.loads(_b64decode(encoded))
        if int(payload.get('exp', 0)) <= int(time.time()):
            raise ValueError('expired')
        if payload.get('role') not in {'member', 'admin'}:
            raise ValueError('role')
        return payload
    except Exception as exc:
        raise HTTPException(status_code=401, detail='Session missing, invalid, or expired') from exc


def _bearer(request: Request) -> str:
    header = request.headers.get('Authorization', '')
    scheme, _, token = header.partition(' ')
    return token.strip() if scheme.lower() == 'bearer' else ''


async def require_user(request: Request) -> dict:
    """Require any signed member or administrator session."""
    token = _bearer(request)
    if not token:
        raise HTTPException(status_code=401, detail='Sign in required')
    return verify_session(token)


async def require_admin(request: Request) -> dict | None:
    """Accept an admin browser session or the legacy maintenance token."""
    bearer = _bearer(request)
    if bearer:
        session = verify_session(bearer)
        if session.get('role') != 'admin':
            raise HTTPException(status_code=403, detail='Administrator access required')
        return session

    if not auth_enabled():
        logger.warning(
            "API_ADMIN_PASSWORD not set - admin endpoint %s open in dev mode",
            request.url.path,
        )
        return None

    token = request.headers.get('X-Admin-Token', '')
    # Constant-time comparison prevents token-timing oracles
    if not hmac.compare_digest(token.encode(), admin_password().encode()):
        raise HTTPException(status_code=401, detail='Admin token missing or invalid')
    return None


def allowed_origins() -> list:
    """
    CORS origins. Set ALLOWED_ORIGINS env var (comma-separated) to override.
    Defaults cover the local dev servers and the published GitHub Pages
    console, so a hosted API works with the live site out of the box.
    """
    import os
    raw = os.getenv('ALLOWED_ORIGINS', '')
    if raw.strip():
        return [o.strip() for o in raw.split(',') if o.strip()]
    return [
        'http://localhost:3000',
        'http://127.0.0.1:3000',
        'http://localhost:8000',
        'http://127.0.0.1:8000',
        'https://bruce12-glitch.github.io',
    ]


def default_db_dir() -> Path:
    return BASE_DIR / 'database'
