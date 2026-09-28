"""
Auth API — SRMIST-only gate.

POST /api/auth/login
  body: { "email": "name@srmist.edu.in" }
  - 200 + { ok, email, domain } when the address is @srmist.edu.in
  - 403 when any other domain is supplied. Nothing else is evaluated.

This is an institutional gate, not a password system: real identity proof
comes from the face pipeline + admin token on mutating routes. The email
gate simply ensures only SRMIST members ever reach the console / enrollment.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.auth import SRMIST_DOMAIN, normalize_email, is_srmist_email

router = APIRouter(prefix='/api/auth', tags=['auth'])


class LoginRequest(BaseModel):
    email: str = ''


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
    return {'ok': True, 'email': email, 'domain': SRMIST_DOMAIN}


@router.get('/policy')
async def auth_policy():
    """Lets the frontend render the rule without hardcoding it twice."""
    return {'domain': SRMIST_DOMAIN, 'suffix': '@' + SRMIST_DOMAIN}
