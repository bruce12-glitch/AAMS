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
