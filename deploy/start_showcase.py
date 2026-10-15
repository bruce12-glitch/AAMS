"""Start the complete showcase with runtime-only, persistent private data."""
from __future__ import annotations

import json
import os
from pathlib import Path
import secrets
import sys


SIGNING_KEYS = ('QR_SECRET_KEY', 'SESSION_SECRET_KEY')


def persistent_secrets(directory: Path, environ) -> None:
    """Keep generated signing keys stable across container replacements."""
    path = directory / 'signing-keys.json'
    if not path.exists():
        values = {key: environ.get(key) or secrets.token_urlsafe(48) for key in SIGNING_KEYS}
        if any(len(value) < 32 or value.startswith('CHANGE_') for value in values.values()):
            raise RuntimeError('Signing keys must have at least 32 characters and cannot be placeholders')
        # Exclusive creation must never replace signing keys from another boot.
        try:
            descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
                json.dump(values, stream)
                stream.flush()
                os.fsync(stream.fileno())
        except FileExistsError:
            pass
    try:
        values = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(values, dict) or any(
            not isinstance(values.get(key), str) or len(values[key]) < 32
            or values[key].startswith('CHANGE_') for key in SIGNING_KEYS
        ):
            raise ValueError
    except (ValueError, TypeError):
        raise RuntimeError('Persistent signing keys are invalid; restore the private volume backup') from None
    path.chmod(0o600)
    for key in SIGNING_KEYS:
        environ.setdefault(key, values[key])


def prepare_runtime(app_dir: Path, environ=None) -> int:
    """Set paths before any app imports; never migrate or overwrite user photos."""
    environ = os.environ if environ is None else environ
    try:
        port = int(environ.get('PORT', '8000'))
        if not 1 <= port <= 65535:
            raise ValueError
    except (ValueError, TypeError):
        raise RuntimeError('PORT must be an integer from 1 to 65535') from None

    volume = environ.get('RAILWAY_VOLUME_MOUNT_PATH')
    if environ.get('RAILWAY_SERVICE_ID') and not volume:
        raise RuntimeError('Attach a persistent volume before starting the Railway service')
    data = Path(environ.get('AAMS_DATA_DIR') or volume or '/data').resolve()
    if volume and not data.is_relative_to(Path(volume).resolve()):
        raise RuntimeError('AAMS_DATA_DIR must be inside the persistent volume')
    dist = Path(environ.get('SPA_DIST_DIR') or app_dir / 'web-dist').resolve()
    if not (dist / 'index.html').is_file():
        raise RuntimeError('The built website is missing; build Dockerfile.showcase')

    # This launcher is always production, regardless of an inherited dev flag.
    environ['AAMS_ENV'] = 'production'
    environ['SPA_DIST_DIR'] = str(dist)
    data.mkdir(parents=True, exist_ok=True, mode=0o700)
    for subdir in ('database', 'images', 'models'):
        (data / subdir).mkdir(exist_ok=True, mode=0o700)

    # Existing DB/evidence paths remain compatible with the private Compose stack.
    images = app_dir / 'images'
    target = data / 'images'
    if images.is_symlink():
        if images.resolve() != target:
            raise RuntimeError('Existing images link points outside this data volume')
    elif images.exists():
        placeholders = list(images.rglob('*')) if images.is_dir() else []
        if not images.is_dir() or any(
            p.is_symlink() or not (p.is_dir() or p.is_file() and p.name == '.gitkeep')
            for p in placeholders
        ):
            raise RuntimeError('Existing photos were preserved; migrate them to the volume before starting')
        for path in sorted(placeholders, key=lambda p: len(p.parts), reverse=True):
            path.rmdir() if path.is_dir() else path.unlink()
        images.rmdir()
    if not images.is_symlink():
        images.symlink_to(target, target_is_directory=True)

    # Host-specific overrides must not move private state off the data volume.
    for key, default in (
        ('DATABASE_PATH', data / 'database' / 'fablab.db'),
        ('INSIGHTFACE_ROOT', data / 'models'),
    ):
        value = Path(environ.get(key) or default).resolve()
        if not value.is_relative_to(data):
            raise RuntimeError(f'{key} must be inside the persistent data directory')
        environ[key] = str(value)
    persistent_secrets(data, environ)
    return port


def main() -> None:
    app_dir = Path(__file__).resolve().parent
    port = prepare_runtime(app_dir)
    sys.path.insert(0, str(app_dir))
    import uvicorn
    uvicorn.run('app.main:app', host='0.0.0.0', port=port, workers=1)


if __name__ == '__main__':
    main()
