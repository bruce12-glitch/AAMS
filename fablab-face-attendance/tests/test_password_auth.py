"""Member passwords: hashing plus email+password login."""

import pytest

from app.auth import (
    MIN_PASSWORD_LEN,
    hash_password,
    normalize_email,
    verify_password,
)


def test_hash_verify_roundtrip():
    stored = hash_password('correct-horse-7')
    assert stored != 'correct-horse-7'
    assert verify_password('correct-horse-7', stored) is True
    assert verify_password('wrong-password', stored) is False


def test_short_password_rejected():
    with pytest.raises(ValueError):
        hash_password('12345')


def test_malformed_hash_never_verifies():
    assert verify_password('anything', 'not-a-hash') is False
    assert verify_password('anything', None) is False


import pytest as _pytest


@_pytest.fixture(scope='module', autouse=True)
def _migrated_schema():
    # Applies pending column migrations (e.g. users.password_hash) to the
    # dev database, exactly as app startup does via init_db().
    from app.database import init_db

    init_db()


def _seed_user(email, password=None):
    from app.database import get_connection

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute('DELETE FROM users WHERE user_id = ?', ('PWDPROBE001',))
        cur.execute(
            'INSERT INTO users (user_id, name, email, payment_status, '
            'password_hash, active) VALUES (?, ?, ?, ?, ?, 1)',
            ('PWDPROBE001', 'Probe User', normalize_email(email), 'active',
             hash_password(password) if password else None))
        conn.commit()
    finally:
        conn.close()


def _drop_user():
    from app.database import get_connection

    conn = get_connection()
    try:
        conn.execute('DELETE FROM users WHERE user_id = ?', ('PWDPROBE001',))
        conn.commit()
    finally:
        conn.close()


def test_login_route_password_flow():
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app, raise_server_exceptions=False)
    try:
        _seed_user('pwdprobe@srmist.edu.in', 's3cret-pass')

        r = client.post('/api/auth/login',
                        json={'email': 'pwdprobe@srmist.edu.in',
                              'password': 's3cret-pass'})
        assert r.status_code == 200, r.text
        assert r.json()['user_id'] == 'PWDPROBE001'

        r = client.post('/api/auth/login',
                        json={'email': 'pwdprobe@srmist.edu.in',
                              'password': 'nope-wrong'})
        assert r.status_code == 403, r.text

        r = client.post('/api/auth/login',
                        json={'email': 'pwdprobe@srmist.edu.in'})
        assert r.status_code == 400, r.text

        r = client.post('/api/auth/login',
                        json={'email': 'ghost@srmist.edu.in',
                              'password': 's3cret-pass'})
        assert r.status_code == 403, r.text
    finally:
        _drop_user()


def test_login_route_without_password_set():
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app, raise_server_exceptions=False)
    try:
        _seed_user('nopwd@srmist.edu.in', None)
        r = client.post('/api/auth/login',
                        json={'email': 'nopwd@srmist.edu.in',
                              'password': 'whatever-1'})
        assert r.status_code == 403, r.text
        assert 'password' in r.json()['detail'].lower()
    finally:
        _drop_user()


def test_min_password_len_exported():
    assert MIN_PASSWORD_LEN >= 6
