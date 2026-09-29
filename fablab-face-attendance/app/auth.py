"""
SRMIST-only authentication for FacePass FabLab.

Rule (product requirement):
  ONLY @srmist.edu.in mail IDs are permitted. No other domain is evaluated
  or accepted — login, enrollment and member creation all reject anything else.

This is deliberately strict and centralized here so frontend + backend share
one definition:
  - normalize: trim + lowercase
  - valid iff matches ^[a-z0-9._%+-]+@srmist\\.edu\\.in$
"""

import re

SRMIST_DOMAIN = 'srmist.edu.in'
SRMIST_SUFFIX = '@' + SRMIST_DOMAIN

# Local-part per RFC-lite: letters, digits and . _ % + -
_SRMIST_RE = re.compile(r'^[a-z0-9._%+\-]+@srmist\.edu\.in$', re.IGNORECASE)


def normalize_email(email) -> str:
    """Trim + lowercase. Non-strings become ''."""
    if not isinstance(email, str):
        return ''
    return email.strip().lower()


def is_srmist_email(email) -> bool:
    """True only for @srmist.edu.in addresses."""
    return bool(_SRMIST_RE.match(normalize_email(email)))


def reject_non_srmist(email) -> str:
    """
    Return the normalized email if valid, else raise ValueError with a
    clear, user-facing message. Keeps route handlers one-liners.
    """
    cleaned = normalize_email(email)
    if not cleaned:
        raise ValueError('SRMIST email is required (e.g. name@srmist.edu.in)')
    if not is_srmist_email(cleaned):
        raise ValueError(
            f'Only {SRMIST_SUFFIX} mail IDs are allowed — "{cleaned}" was rejected'
        )
    return cleaned


# ------------------------------------------------------------------ #
# Member passwords — console sign-in requires SRMIST email + password.
# PBKDF2-HMAC-SHA256 with a per-user salt; stored as
#   pbkdf2$<iterations>$<salt_hex>$<hash_hex>
# so a database leak never exposes usable passwords.
# ------------------------------------------------------------------ #

MIN_PASSWORD_LEN = 6
_PBKDF2_ITERATIONS = 200_000


def hash_password(password: str) -> str:
    """Hash a new member password. Raises ValueError if too short."""
    import hashlib
    import secrets

    if not isinstance(password, str) or len(password) < MIN_PASSWORD_LEN:
        raise ValueError(
            f'Password must be at least {MIN_PASSWORD_LEN} characters'
        )
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt,
                             _PBKDF2_ITERATIONS)
    return (f'pbkdf2${_PBKDF2_ITERATIONS}${salt.hex()}${dk.hex()}')


def verify_password(password: str, stored: str) -> bool:
    """Constant-time check of a password against a stored hash."""
    import hashlib
    import hmac

    try:
        algo, iters, salt_hex, hash_hex = (stored or '').split('$')
        if algo != 'pbkdf2':
            return False
        dk = hashlib.pbkdf2_hmac('sha256', (password or '').encode('utf-8'),
                                 bytes.fromhex(salt_hex), int(iters))
        return hmac.compare_digest(dk.hex(), hash_hex)
    except Exception:
        return False
