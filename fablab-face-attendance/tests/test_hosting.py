"""Deployment boundaries: same-origin routing and durable private runtime state."""
import importlib.util
import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app.web import mount_console


spec = importlib.util.spec_from_file_location(
    'showcase_launcher', Path(__file__).resolve().parents[2] / 'deploy' / 'start_showcase.py')
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


@pytest.fixture
def runtime(tmp_path):
    app = tmp_path / 'app'
    app.mkdir()
    dist = app / 'web-dist'
    dist.mkdir()
    (dist / 'index.html').write_text('<html>AAMS console</html>')
    return app, {'AAMS_DATA_DIR': str(tmp_path / 'data')}


def test_console_serves_assets_without_shadowing_api_or_private_files(tmp_path):
    dist = tmp_path / 'web-dist'
    dist.mkdir()
    (dist / 'index.html').write_text('<html>AAMS console</html>')
    (dist / 'assets').mkdir()
    (dist / 'assets' / 'app.js').write_text('console.log("AAMS")')
    (tmp_path / 'signing-keys.json').write_text('PRIVATE')
    app = FastAPI()

    @app.get('/health')
    def health():
        return {'status': 'ok'}

    @app.get('/api/private')
    def private():
        from fastapi import HTTPException
        raise HTTPException(401, 'Authentication required')

    mount_console(app, dist)
    client = TestClient(app)
    assert 'AAMS console' in client.get('/').text
    assert client.get('/assets/app.js').status_code == 200
    assert client.get('/health').json() == {'status': 'ok'}
    assert client.get('/api/private').status_code == 401
    for path in ('/api/missing', '/assets/missing.js', '/signing-keys.json',
                 '/images/student.jpg', '/database/fablab.db', '/%2e%2e/signing-keys.json'):
        response = client.get(path)
        assert response.status_code == 404
        assert 'PRIVATE' not in response.text


def test_missing_console_build_fails_closed(tmp_path):
    with pytest.raises(RuntimeError, match='built website'):
        mount_console(FastAPI(), tmp_path)


def test_signing_keys_and_photos_survive_replacement_container(runtime, tmp_path):
    app, env = runtime
    assert launcher.prepare_runtime(app, env) == 8000
    keys = {key: env[key] for key in launcher.SIGNING_KEYS}
    assert env['AAMS_ENV'] == 'production'
    assert (app / 'images').is_symlink()
    (app / 'images' / 'student.jpg').write_bytes(b'photo')
    keyfile = tmp_path / 'data' / 'signing-keys.json'
    assert keyfile.stat().st_mode & 0o777 == 0o600
    second_app = tmp_path / 'replacement'
    second_app.mkdir()
    second_env = {'AAMS_DATA_DIR': env['AAMS_DATA_DIR'], 'SPA_DIST_DIR': env['SPA_DIST_DIR'], 'PORT': '3100'}
    assert launcher.prepare_runtime(second_app, second_env) == 3100
    assert {key: second_env[key] for key in launcher.SIGNING_KEYS} == keys
    assert (second_app / 'images' / 'student.jpg').read_bytes() == b'photo'
    assert second_env['DATABASE_PATH'] == env['DATABASE_PATH']
    assert second_env['INSIGHTFACE_ROOT'] == env['INSIGHTFACE_ROOT']


@pytest.mark.parametrize('port', ['0', '65536', 'x', '8000.5', ''])
def test_invalid_host_port_is_rejected(runtime, port):
    app, env = runtime
    env['PORT'] = port
    with pytest.raises(RuntimeError, match='PORT'):
        launcher.prepare_runtime(app, env)


def test_railway_requires_volume(runtime):
    app, env = runtime
    env['RAILWAY_SERVICE_ID'] = 'test-service'
    with pytest.raises(RuntimeError, match='persistent volume'):
        launcher.prepare_runtime(app, env)
    env['RAILWAY_VOLUME_MOUNT_PATH'] = env['AAMS_DATA_DIR']
    assert launcher.prepare_runtime(app, env) == 8000


@pytest.mark.parametrize('key', ['AAMS_DATA_DIR', 'DATABASE_PATH', 'INSIGHTFACE_ROOT'])
def test_private_paths_cannot_escape_volume(runtime, tmp_path, key):
    app, env = runtime
    env['RAILWAY_VOLUME_MOUNT_PATH'] = env['AAMS_DATA_DIR']
    env[key] = str(tmp_path / 'elsewhere')
    with pytest.raises(RuntimeError, match='persistent'):
        launcher.prepare_runtime(app, env)


def test_existing_photos_are_never_overwritten(runtime):
    app, env = runtime
    (app / 'images').mkdir()
    photo = app / 'images' / 'photo.jpg'
    photo.write_bytes(b'important')
    with pytest.raises(RuntimeError, match='preserved'):
        launcher.prepare_runtime(app, env)
    assert photo.read_bytes() == b'important'


def test_source_placeholder_directories_can_be_linked(runtime):
    app, env = runtime
    placeholders = app / 'images' / 'enrollment'
    placeholders.mkdir(parents=True)
    (placeholders / '.gitkeep').touch()
    launcher.prepare_runtime(app, env)
    assert (app / 'images').is_symlink()


def test_invalid_existing_signing_keys_are_not_regenerated(runtime, tmp_path):
    app, env = runtime
    data = Path(env['AAMS_DATA_DIR'])
    data.mkdir()
    path = data / 'signing-keys.json'
    path.write_text(json.dumps({'QR_SECRET_KEY': 'short'}))
    previous = path.read_bytes()
    with pytest.raises(RuntimeError, match='restore'):
        launcher.prepare_runtime(app, env)
    assert path.read_bytes() == previous


def test_face_model_uses_persistent_cache(monkeypatch, tmp_path):
    from app import face_engine
    observed = {}

    class FakeAnalysis:
        def __init__(self, **kwargs):
            observed.update(kwargs)

        def prepare(self, **_kwargs):
            pass

    monkeypatch.setattr(face_engine, '_FaceAnalysis', FakeAnalysis)
    monkeypatch.setenv('INSIGHTFACE_ROOT', str(tmp_path))
    face_engine.FaceEngine()
    assert observed['root'] == str(tmp_path)
    assert observed['providers'] == ['CPUExecutionProvider']
