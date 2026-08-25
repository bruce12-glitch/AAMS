"""
Tests for API security guards (§27.2): X-Admin-Token requirement,
dev-open fallback when unconfigured, and CORS origin resolution.
"""

import importlib

import pytest
from fastapi import HTTPException

import app.security as sec


class FakeURL:
    def __init__(self, path='/api/users'):
        self.path = path


class FakeRequest:
    def __init__(self, path='/api/users'):
        self.url = FakeURL(path)
        self.headers = {}


@pytest.fixture(autouse=True)
def reset_env(monkeypatch):
    monkeypatch.delenv('ALLOWED_ORIGINS', raising=False)
    yield


# ---------------------------------------------------------------- #
# auth_enabled / admin_password resolution
# ---------------------------------------------------------------- #

def test_placeholder_password_disables_auth(monkeypatch):
    for placeholder in ('', 'CHANGE_THIS', 'your_admin_password_here'):
        monkeypatch.setattr(sec, 'admin_password', lambda p=placeholder: p)
        assert sec.auth_enabled() is False


def test_real_password_enables_auth(monkeypatch):
    monkeypatch.setattr(sec, 'admin_password', lambda: 's3cret')
    assert sec.auth_enabled() is True


# ---------------------------------------------------------------- #
# require_admin behaviour
# ---------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_dev_open_mode_allows_when_unconfigured(monkeypatch):
    monkeypatch.setattr(sec, 'auth_enabled', lambda: False)
    await sec.require_admin(FakeRequest())  # must not raise


@pytest.mark.asyncio
async def test_missing_token_rejected_when_configured(monkeypatch):
    monkeypatch.setattr(sec, 'auth_enabled', lambda: True)
    monkeypatch.setattr(sec, 'admin_password', lambda: 's3cret')

    with pytest.raises(HTTPException) as exc:
        await sec.require_admin(FakeRequest())
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_wrong_token_rejected(monkeypatch):
    monkeypatch.setattr(sec, 'auth_enabled', lambda: True)
    monkeypatch.setattr(sec, 'admin_password', lambda: 's3cret')

    req = FakeRequest()
    req.headers = {'X-Admin-Token': 'wrong'}

    with pytest.raises(HTTPException) as exc:
        await sec.require_admin(req)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_correct_token_passes(monkeypatch):
    monkeypatch.setattr(sec, 'auth_enabled', lambda: True)
    monkeypatch.setattr(sec, 'admin_password', lambda: 's3cret')

    req = FakeRequest()
    req.headers = {'X-Admin-Token': 's3cret'}

    await sec.require_admin(req)  # no exception


# ---------------------------------------------------------------- #
# CORS origins
# ---------------------------------------------------------------- #

def test_default_cors_origins():
    importlib.reload(sec)
    origins = sec.allowed_origins()
    assert 'http://localhost:3000' in origins
    assert all(o.startswith('http') for o in origins)


def test_env_override_cors_origins(monkeypatch):
    monkeypatch.setenv('ALLOWED_ORIGINS',
                       'https://lab.srmist.edu.in , https://aams.example.com')
    importlib.reload(sec)
    try:
        assert sec.allowed_origins() == [
            'https://lab.srmist.edu.in', 'https://aams.example.com'
        ]
    finally:
        importlib.reload(sec)
