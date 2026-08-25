"""
Security helpers for FacePass FabLab (§27.2 API Security).

Admin protection: mutating endpoints require header
    X-Admin-Token: <API_ADMIN_PASSWORD from .env>

If no password is configured (placeholder/empty) the guard runs in
dev-open mode and logs a warning — convenient locally, loud in logs.
"""

import logging
from pathlib import Path

from fastapi import HTTPException, Request

from app.config import get_security_config, BASE_DIR

logger = logging.getLogger(__name__)

_PLACEHOLDERS = {"", "CHANGE_THIS", "your_admin_password_here"}


def admin_password() -> str:
    try:
        return (get_security_config().get('api_admin_password') or '').strip()
    except Exception:
        return ''


def auth_enabled() -> bool:
    return admin_password() not in _PLACEHOLDERS


async def require_admin(request: Request) -> None:
    """FastAPI dependency guarding admin/mutating routes."""
    if not auth_enabled():
        logger.warning(
            "API_ADMIN_PASSWORD not set - admin endpoint %s open in dev mode",
            request.url.path,
        )
        return

    token = request.headers.get('X-Admin-Token', '')
    if token != admin_password():
        raise HTTPException(status_code=401, detail='Admin token missing or invalid')


def allowed_origins() -> list:
    """
    CORS origins. Set ALLOWED_ORIGINS env var (comma-separated) to override.
    Defaults to the local Vite dev server + same-origin.
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
    ]


def default_db_dir() -> Path:
    return BASE_DIR / 'database'
