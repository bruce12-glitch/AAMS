"""
API hardening: admin guards on credential/mutating routes, sign-in brute
force limit, and input validation (member IDs, upload size).
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.security import admin_password, auth_enabled

# True when API_ADMIN_PASSWORD is configured (real deployments and the dev
# .env). False in a placeholder setup, where require_admin is dev-open by
# design — the assertions below then only check that nothing else broke.
ADMIN_CONFIGURED = auth_enabled()


@pytest.fixture(scope='module')
def client():
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture(scope='module', autouse=True)
def _migrated_schema():
    # Applies pending column migrations (e.g. users.password_hash).
    from app.database import init_db

    init_db()


def _hdr():
    return {'X-Admin-Token': admin_password()} if ADMIN_CONFIGURED else {}


def _user_id():
    return 'HARDENPROBE001'


# ---------------------------------------------------------------- #
# Admin guards
# ---------------------------------------------------------------- #

# (method, path, json body)
GUARDED = [
    ('GET', '/api/users/{uid}/qr', None),
    ('POST', '/api/alerts/1/ack', None),
    ('POST', '/api/alerts/1/approve', None),
    ('POST', '/api/occupants/{uid}/exit', None),
    ('POST', '/api/occupants/scan', None),
]


@pytest.mark.parametrize('method,path,body', GUARDED)
def test_guarded_route_needs_admin_token(client, method, path, body):
    url = path.format(uid=_user_id())
    r = client.request(method, url, json=body)
    if ADMIN_CONFIGURED:
        assert r.status_code == 401, f'{method} {url} -> {r.status_code}'
    else:
        assert r.status_code != 401


@pytest.mark.parametrize('method,path,body', GUARDED)
def test_guarded_route_accepts_valid_token(client, method, path, body):
    url = path.format(uid=_user_id())
    r = client.request(method, url, json=body, headers=_hdr())
    assert r.status_code != 401, f'{method} {url} -> {r.status_code}: {r.text}'


def test_wrong_token_rejected(client):
    r = client.get(f'/api/users/{_user_id()}/qr',
                   headers={'X-Admin-Token': 'definitely-not-the-token'})
    if ADMIN_CONFIGURED:
        assert r.status_code == 401


# ---------------------------------------------------------------- #
# Sign-in brute-force limit
# ---------------------------------------------------------------- #

def test_login_rate_limit_returns_429(client, monkeypatch):
    from app.ratelimit import reset_rate_limits

    monkeypatch.setenv('LOGIN_RATE_LIMIT', '3')
    reset_rate_limits()

    payload = {'email': 'bruteforce@srmist.edu.in', 'password': 'nope-nope'}
    codes = [client.post('/api/auth/login', json=payload).status_code
             for _ in range(5)]

    assert codes[:3] != [429] * 3, 'first attempts must not be limited'
    assert codes[3] == 429 and codes[4] == 429, f'got {codes}'

    r = client.post('/api/auth/login', json=payload)
    assert r.headers.get('Retry-After'), '429 must carry Retry-After'
    assert 429 == r.status_code


def test_login_limit_scopes_to_one_mail_id(client, monkeypatch):
    from app.ratelimit import reset_rate_limits

    monkeypatch.setenv('LOGIN_RATE_LIMIT', '2')
    reset_rate_limits()

    a = {'email': 'one@srmist.edu.in', 'password': 'nope-nope'}
    b = {'email': 'two@srmist.edu.in', 'password': 'nope-nope'}
    codes = [client.post('/api/auth/login', json=p).status_code
             for p in (a, a, a, b)]

    assert codes[2] == 429, f'third guess for one mail must be cut off: {codes}'
    # The per-IP budget is deliberately wider, so one account being probed
    # does not lock out everyone else behind the same address.
    assert codes[3] != 429, f'another mail on the same IP must still work: {codes}'


# ---------------------------------------------------------------- #
# Input validation
# ---------------------------------------------------------------- #

@pytest.mark.parametrize('bad', ['', ' ../evil', 'a/b', 'a b', 'x' * 65,
                                 'name@host', '…'])
def test_user_id_validation_rejects_unsafe_ids(bad):
    from app.security import validate_user_id

    with pytest.raises(ValueError):
        validate_user_id(bad)


@pytest.mark.parametrize('ok', ['RA2111003010128', 'sample-0001', 'A.B_C-1'])
def test_user_id_validation_accepts_plain_ids(ok):
    from app.security import validate_user_id

    assert validate_user_id(ok) == ok


def test_create_user_rejects_path_traversal_id(client):
    r = client.post('/api/users',
                    json={'user_id': '../escape', 'name': 'Nope'},
                    headers=_hdr())
    assert r.status_code == 400, r.text
    assert 'user_id' in r.json()['detail']


def test_enroll_rejects_more_than_ten_images(client):
    r = client.post('/api/users/enroll',
                    json={'user_id': _user_id(), 'name': 'Too Many',
                          'consent_given': True,
                          'images': ['data:image/jpeg;base64,AAAA'] * 11},
                    headers=_hdr())
    assert r.status_code == 422, r.text


def test_decode_image_rejects_oversized_payload():
    from app.vision import MAX_IMAGE_BASE64_CHARS, decode_image

    with pytest.raises(ValueError, match='too large'):
        decode_image('A' * (MAX_IMAGE_BASE64_CHARS + 1))


def test_decode_image_rejects_garbage():
    from app.vision import decode_image

    with pytest.raises(ValueError):
        decode_image('not-base64-at-all!!')


# ---------------------------------------------------------------- #
# /api/users payload hygiene + enrolled flag
# ---------------------------------------------------------------- #

def test_list_users_strips_credentials_and_reports_enrolled():
    from app.database import get_connection

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute('DELETE FROM users WHERE user_id = ?', ('HARDPROBE01',))
        cur.execute('DELETE FROM users WHERE user_id = ?', ('HARDPROBE02',))
        cur.execute(
            'INSERT INTO users (user_id, name, email, password_hash, '
            'face_embedding, active) VALUES (?, ?, ?, ?, ?, 1)',
            ('HARDPROBE01', 'With Face', 'face@srmist.edu.in',
             'pbkdf2$200000$abc$def', b'\x00' * 4))
        cur.execute(
            'INSERT INTO users (user_id, name, email, password_hash, active) '
            'VALUES (?, ?, ?, ?, 1)',
            ('HARDPROBE02', 'No Face', 'noface@srmist.edu.in',
             'pbkdf2$200000$abc$def'))
        conn.commit()
    finally:
        conn.close()

    try:
        client = TestClient(app, raise_server_exceptions=False)
        users = {u['user_id']: u
                 for u in client.get('/api/users').json()['users']}

        with_face = users['HARDPROBE01']
        without_face = users['HARDPROBE02']

        assert with_face['enrolled'] is True, 'member with an embedding must read as enrolled'
        assert without_face['enrolled'] is False

        for u in (with_face, without_face):
            assert u['password_hash'] is None, 'hashes must never reach the client'
    finally:
        conn = get_connection()
        try:
            conn.execute('DELETE FROM users WHERE user_id IN (?, ?)',
                         ('HARDPROBE01', 'HARDPROBE02'))
            conn.commit()
        finally:
            conn.close()
