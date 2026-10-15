"""Exercise the complete container and volume on a disposable CI runner."""
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import tempfile
import time
import urllib.error
import urllib.request


def docker(*args, capture=False):
    result = subprocess.run(['docker', *args], check=True, capture_output=capture, text=True)
    return result.stdout.strip() if capture else None


def main():
    if os.getenv('GITHUB_ACTIONS') != 'true':
        raise RuntimeError('This cleanup test is restricted to disposable GitHub Actions runners')
    suffix = secrets.token_hex(5)
    image, container, volume = (f'aams-hosted-{suffix}{end}' for end in ('-image', '-app', '-data'))
    admin, member = secrets.token_urlsafe(24), secrets.token_urlsafe(24)
    base = ''

    def request(path, body=None, token=None):
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = 'Bearer ' + token
        req = urllib.request.Request(base + path, headers=headers,
                                     data=json.dumps(body).encode() if body is not None else None)
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
        raise RuntimeError('Complete showcase did not become ready')

    def start(envfile):
        nonlocal base
        docker('run', '-d', '--name', container, '--env-file', str(envfile),
               '--mount', f'type=volume,src={volume},dst=/data',
               '-p', '127.0.0.1::8080', image)
        address = docker('port', container, '8080/tcp', capture=True)
        base = 'http://' + address
        wait_ready()

    try:
        docker('build', '-f', 'Dockerfile.showcase', '-t', image, '.')
        docker('volume', 'create', volume)
        with tempfile.TemporaryDirectory(prefix='aams-hosted-') as temp:
            envfile = Path(temp) / 'runtime.env'
            envfile.touch(mode=0o600)
            envfile.write_text('\n'.join([
                'PORT=8080', 'ADMIN_EMAIL=admin@srmist.edu.in',
                f'API_ADMIN_PASSWORD={admin}', f'AAMS_ACCESS_PASSWORD={member}',
                'RAILWAY_SERVICE_ID=ci-service', 'RAILWAY_VOLUME_MOUNT_PATH=/data',
            ]) + '\n')
            start(envfile)
            with urllib.request.urlopen(base) as response:
                html = response.read().decode()
                assert '<div id="root"' in html
                asset = re.search(r'src="([^"]+\.js)"', html).group(1)
            with urllib.request.urlopen(base + asset) as response:
                assert response.status == 200
            try:
                request('/api/auth/login', {'email': 'outside@example.org', 'password': member})
                raise AssertionError('Non-SRMIST email was accepted')
            except urllib.error.HTTPError as error:
                assert error.code == 403
            session = request('/api/auth/login', {'email': 'admin@srmist.edu.in', 'password': admin})['token']
            request('/api/users', {'user_id': 'HOSTED-CI', 'name': 'Hosted CI Student',
                                   'email': 'hosted.ci@srmist.edu.in', 'department': 'CSE', 'year': 3}, session)
            docker('exec', container, 'python', '-c',
                   "from pathlib import Path; Path('/app/images/persistence.txt').write_text('retained')")
            for path in ('/signing-keys.json', '/data/signing-keys.json', '/images/persistence.txt',
                         '/database/fablab.db', '/api/nonexistent'):
                try:
                    urllib.request.urlopen(base + path)
                    raise AssertionError('Private/missing route was exposed: ' + path)
                except urllib.error.HTTPError as error:
                    assert error.code == 404
            # Recreate, rather than just restart: the writable container layer is lost.
            docker('rm', '-f', container)
            start(envfile)
            assert any(row['user_id'] == 'HOSTED-CI' for row in request('/api/users', token=session)['users'])
            docker('exec', container, 'python', '-c',
                   "from pathlib import Path; assert Path('/app/images/persistence.txt').read_text() == 'retained'")
            print('Single-origin UI/API, SRMIST auth, private files and student/photo/session persistence after replacement: PASS')
    finally:
        subprocess.run(['docker', 'rm', '-f', container], check=False)
        subprocess.run(['docker', 'volume', 'rm', volume], check=False)
        subprocess.run(['docker', 'image', 'rm', image], check=False)


if __name__ == '__main__':
    main()
