"""Signed browser sessions and role-based API access."""

import time

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
import app.security as security
import api.routes_auth as routes_auth


class FakeURL:
    path = '/api/users/enroll'


class FakeRequest:
    url = FakeURL()

    def __init__(self, token=''):
        self.headers = {'Authorization': f'Bearer {token}'} if token else {}


def _token(role='member'):
    return security.issue_session(
        email=f'{role}@srmist.edu.in', user_id=role.upper(),
        name=role.title(), role=role)['token']


def test_session_roundtrip_and_tamper_rejection():
    token = _token()
    assert security.verify_session(token)['role'] == 'member'
    with pytest.raises(HTTPException) as exc:
        security.verify_session(token[:-1] + ('A' if token[-1] != 'A' else 'B'))
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_admin_session_passes_admin_guard():
    session = await security.require_admin(FakeRequest(_token('admin')))
    assert session['role'] == 'admin'


@pytest.mark.asyncio
async def test_member_session_cannot_mutate():
    with pytest.raises(HTTPException) as exc:
        await security.require_admin(FakeRequest(_token('member')))
    assert exc.value.status_code == 403


def test_protected_read_requires_session():
    client = TestClient(app, raise_server_exceptions=False)
    assert client.get('/api/users').status_code == 401
    response = client.get(
        '/api/users', headers={'Authorization': f'Bearer {_token()}'})
    assert response.status_code == 200


def test_admin_login_issues_admin_session(monkeypatch):
    monkeypatch.setattr(routes_auth, 'admin_email', lambda: 'admin@srmist.edu.in')
    monkeypatch.setattr(routes_auth, 'admin_password', lambda: 'showcase-password')
    monkeypatch.setattr(routes_auth, 'auth_enabled', lambda: True)
    monkeypatch.setattr(routes_auth, 'session_security_ready', lambda: True)
    client = TestClient(app, raise_server_exceptions=False)
    response = client.post('/api/auth/login', json={
        'email': 'admin@srmist.edu.in',
        'password': 'showcase-password',
    })
    assert response.status_code == 200
    body = response.json()
    assert body['role'] == 'admin'
    assert security.verify_session(body['token'])['role'] == 'admin'


def test_expired_session_rejected(monkeypatch):
    token = _token()
    monkeypatch.setattr(time, 'time', lambda: 99999999999)
    with pytest.raises(HTTPException):
        security.verify_session(token)
