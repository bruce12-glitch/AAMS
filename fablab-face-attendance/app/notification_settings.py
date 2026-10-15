"""Private, restart-safe Telegram settings stored beside the database."""

import json
import os
import tempfile
from pathlib import Path

from app.config import get_database_path


def settings_path():
    return Path(get_database_path()).parent / 'notification-settings.json'


def read_settings():
    path = settings_path()
    if not path.exists():
        return {}
    with path.open(encoding='utf-8') as stream:
        return json.load(stream)


def save_settings(values):
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    current = read_settings()
    # An empty token from a form keeps the existing private credential.
    if not values.get('bot_token'):
        values = {key: value for key, value in values.items() if key != 'bot_token'}
    current.update(values)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix='.notifications-')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(current, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
