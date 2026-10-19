"""Validate the private Docker stack in an ephemeral CI runner."""
import json
import os
import secrets
import subprocess
import time
import urllib.request
from pathlib import Path


def compose(*args):
    subprocess.run(['docker', 'compose', *args], check=True)


def request(path, body=None, token=None):
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    req = urllib.request.Request('http://127.0.0.1:8000' + path,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers=headers)
    with urllib.request.urlopen(req, timeout=10) as response:
        return json.load(response)


def wait_ready():
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        try:
            if request('/ready')['status'] == 'ready':
                return
        except (OSError, ValueError):
            pass
        time.sleep(1)
    raise RuntimeError('Docker API did not become ready')


def main():
    if os.getenv('GITHUB_ACTIONS') != 'true':
        raise RuntimeError('This destructive cleanup test is restricted to disposable GitHub Actions runners')
    admin = secrets.token_urlsafe(24)
    member = secrets.token_urlsafe(24)
    target = Path('fablab-face-attendance/.env')
    if target.exists():
        raise RuntimeError('CI smoke requires an empty disposable checkout; existing environment is preserved')
    target.write_text('\n'.join([
        'AAMS_ENV=production', 'ADMIN_EMAIL=admin@srmist.edu.in',
        f'API_ADMIN_PASSWORD={admin}', f'AAMS_ACCESS_PASSWORD={member}',
        f'QR_SECRET_KEY={secrets.token_urlsafe(48)}',
        f'SESSION_SECRET_KEY={secrets.token_urlsafe(48)}',
        'TELEGRAM_BOT_TOKEN=', 'TELEGRAM_CHAT_ID=',
    ]) + '\n')
    target.chmod(0o600)
    try:
        compose('up', '--build', '-d', 'api', 'web')
        wait_ready()
        session = request('/api/auth/login', {'email': 'admin@srmist.edu.in', 'password': admin})['token']
        request('/api/users', {'user_id': 'CI-STUDENT', 'name': 'CI Student', 'email': 'ci.student@srmist.edu.in'}, session)
        compose('restart', 'api')
        wait_ready()
        assert any(row['user_id'] == 'CI-STUDENT' for row in request('/api/users', token=session)['users'])
        with urllib.request.urlopen('http://127.0.0.1:8090/health') as response:
            assert json.load(response)['status'] == 'ok'
        with urllib.request.urlopen('http://127.0.0.1:8090') as response:
            assert b'<div id="root"' in response.read()
        print('Docker startup, secure login, student persistence after restart and nginx proxy: PASS')
        # Full dependencies and the persistent model volume are available here.
        # This test never sends to a real bot or modifies the stack's student DB.
        compose('exec', '-T', '-e', 'AAMS_REAL_VISION_TEST=1', 'api',
                'python', '-m', 'pytest', 'tests/test_real_vision.py', '-q', '-s', '--tb=short')
    finally:
        compose('down', '--volumes')
        target.unlink(missing_ok=True)


if __name__ == '__main__':
    main()
