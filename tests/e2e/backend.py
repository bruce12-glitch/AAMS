"""Disposable browser-test API with controlled inference and Telegram transport."""
import json
import os
import secrets
from pathlib import Path

root = Path(os.environ['AAMS_E2E_DIR'])
credentials = json.loads((root / 'credentials.json').read_text())
os.environ.update(AAMS_ENV='production', ADMIN_EMAIL=credentials['email'],
                  API_ADMIN_PASSWORD=credentials['password'],
                  AAMS_ACCESS_PASSWORD=credentials['member_password'],
                  SESSION_SECRET_KEY=secrets.token_urlsafe(48),
                  QR_SECRET_KEY=secrets.token_urlsafe(48),
                  DATABASE_PATH=str(root / 'showcase.db'),
                  # Test navigation/polling compresses a full rehearsal into a
                  # minute. Keep production's default 120/min protection intact;
                  # use a larger budget only in this disposable test subprocess.
                  RATE_LIMIT_PER_MIN='1000')
import numpy as np
import app.vision as vision
embedding = np.linspace(-1, 1, 512)
embedding /= np.linalg.norm(embedding)
vision.analyze_frame = lambda frame: {
    'face_count': 1, 'quality_passed': True, 'quality_reasons': [],
    'embedding': embedding.copy(),
}
def initialize_model(*, retry=False):
    vision._ENGINE = object()
    return vision._ENGINE
vision.get_engine = initialize_model

# Exercise the actual Telegram SDK without contacting Telegram or using a token.
# The browser test supplies only its own pairing command as a fixture update.
from telegram import Bot as RealBot
from telegram.request import BaseRequest
import telegram
class TelegramRequest(BaseRequest):
    @property
    def read_timeout(self): return 5
    async def initialize(self): pass
    async def shutdown(self): pass
    async def do_request(self, url, method, request_data=None, **kwargs):
        endpoint = url.rsplit('/', 1)[-1]
        chat = {'id': 7654321, 'type': 'private', 'first_name': 'Browser Test Recipient'}
        if endpoint == 'getMe':
            result = {'id': 123456, 'is_bot': True, 'first_name': 'Test Bot', 'username': 'AAMS_test_bot'}
        elif endpoint == 'getWebhookInfo':
            result = {'url': '', 'has_custom_certificate': False, 'pending_update_count': 0}
        elif endpoint == 'getUpdates':
            fixture = root / 'telegram-update.json'
            result = json.loads(fixture.read_text()) if fixture.exists() else []
        elif endpoint == 'getChat':
            result = {**chat, 'accent_color_id': 1, 'max_reaction_count': 0}
        elif endpoint == 'sendMessage':
            result = {'message_id': 1, 'date': 1, 'chat': chat, 'text': request_data.parameters['text']}
        else:
            raise AssertionError(endpoint)
        return 200, json.dumps({'ok': True, 'result': result}).encode()
telegram.Bot = lambda token, request: RealBot(token=token, request=TelegramRequest(), get_updates_request=TelegramRequest())

# Controlled records live ONLY in this disposable browser-test database. They
# verify that a previously seeded database is not presented as current evidence.
from app.database import init_db, get_connection
init_db()
with get_connection() as conn:
    for source, reason, compared in [
        ('legacy', 'Historical fixture: origin unrecorded', None),
        ('sample', 'Demo fixture: not security evidence', 1),
        ('webcam', 'Controlled browser review item', 1),
        ('snapshot', 'No face detected in controlled capture', 0),
    ]:
        event_id = conn.execute('''INSERT INTO entry_logs
            (decision, reason, tag, similarity, event_source, comparison_performed)
            VALUES ('DENIED', ?, 'unknown', 0.25, ?, ?)''', (reason, source, compared)).lastrowid
        if source != 'snapshot':
            conn.execute('''INSERT INTO alerts
                (alert_type, message, event_source, entry_log_id, sent_status)
                VALUES ('UNKNOWN', ?, ?, ?, 'fixture')''', (reason, source, event_id))
import uvicorn
uvicorn.run('app.main:app', host='127.0.0.1', port=8000, log_level='warning')
