"""Showcase integration tests: API/database and controlled Telegram transport."""
import asyncio
import json

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.alerts import AlertService


@pytest.fixture
def showcase(tmp_path, monkeypatch):
    import app.database as db
    import app.notification_settings as settings
    import app.config as config
    import app.security as security
    monkeypatch.setattr(db, 'DATABASE_PATH', tmp_path / 'showcase.db')
    monkeypatch.setattr(config, 'get_database_path', lambda: tmp_path / 'showcase.db')
    monkeypatch.setattr(settings, 'settings_path', lambda: tmp_path / 'notification-settings.json')
    monkeypatch.setattr(security, 'get_security_config', lambda: {'api_admin_password': 'integration-admin-credential', 'qr_secret_key': 'integration-qr-secret'})
    monkeypatch.setenv('SESSION_SECRET_KEY', 'integration-session-secret-that-is-long-enough')
    monkeypatch.setenv('AAMS_ACCESS_PASSWORD', 'integration-member-credential')
    db.init_db()
    admin = security.issue_session(email='admin@srmist.edu.in', user_id='ADMIN', name='Administrator', role='admin')
    member = security.issue_session(email='member@srmist.edu.in', user_id='MEMBER', name='Member')
    return TestClient(app), {'Authorization': 'Bearer ' + admin['token']}, {'Authorization': 'Bearer ' + member['token']}, db


def student_payload():
    return {'user_id': 'STUDENT-001', 'name': 'Student One', 'email': 'student.one@srmist.edu.in',
            'phone': '9000000000', 'department': 'CSE', 'year': 3, 'section': 'A', 'payment_status': 'active'}


def test_student_crud_and_role_guards(showcase):
    client, admin, member, _db = showcase
    payload = student_payload()
    assert client.post('/api/users', json=payload, headers=member).status_code == 403
    assert client.post('/api/users', json=payload, headers=admin).status_code == 200
    records = client.get('/api/users', headers=member).json()['users']
    assert records[0]['department'] == 'CSE' and records[0]['year'] == 3
    assert records[0]['enrolled'] is False
    assert client.put('/api/users/STUDENT-001', json={'name': 'Edited Student', 'year': 4}, headers=admin).status_code == 200
    assert client.put('/api/users/STUDENT-001', json={'email': 'outside@example.org'}, headers=admin).status_code == 403
    assert client.put('/api/users/STUDENT-001', json={'payment_status': 'nonsense'}, headers=admin).status_code == 422
    assert client.put('/api/users/STUDENT-001', json={'payment_expiry': '2026-13-99'}, headers=admin).status_code == 422
    assert client.put('/api/users/STUDENT-001', json={'name': None}, headers=admin).status_code == 400
    assert client.post('/api/users', json={**payload, 'user_id': 'OTHER'}, headers=admin).status_code == 409
    assert client.delete('/api/users/STUDENT-001', headers=admin).status_code == 200
    assert client.get('/api/users', headers=admin).json()['users'] == []


def test_private_settings_and_automatic_student_notification(showcase):
    client, admin, member, db = showcase
    values = {'enabled': True, 'bot_token': '123456:' + 'a' * 30, 'chat_id': '-10012345678', 'daily_report_time': '19:30'}
    assert client.put('/api/notify/settings', json=values, headers=member).status_code == 403
    assert client.put('/api/notify/settings', json=values, headers=admin).status_code == 200
    response = client.get('/api/notify/status', headers=admin)
    assert values['bot_token'] not in response.text and 'bot_token' not in response.json()
    assert response.json()['daily_report_time'] == '19:30'
    values['bot_token'] = ''
    assert client.put('/api/notify/settings', json=values, headers=admin).status_code == 200
    from app.config import get_telegram_config
    assert get_telegram_config()['bot_token'].endswith('a' * 30)
    values['enabled'] = False
    client.put('/api/notify/settings', json=values, headers=admin)
    assert client.post('/api/users', json=student_payload(), headers=admin).status_code == 200
    with db.get_connection() as conn:
        row = conn.execute("SELECT * FROM alerts WHERE alert_type='ENROLLMENT'").fetchone()
        assert 'Student One' in row['message'] and row['sent_status'] == 'pending'
    bad = client.put('/api/notify/settings', json={**values, 'bot_token': 'PRIVATE-invalid-token'}, headers=admin)
    assert bad.status_code == 422 and 'PRIVATE-invalid-token' not in bad.text


def test_announcement_failure_is_retained_and_retried(showcase, monkeypatch):
    client, admin, _member, _db = showcase
    calls = []
    async def send(self, text, image_path=None):
        calls.append(text)
        return (len(calls) > 1), 'queued' if len(calls) == 1 else 'Delivered to Telegram'
    def initialize(self):
        self.enabled = True
        self.bot = object()
    monkeypatch.setattr(AlertService, '_send', send)
    monkeypatch.setattr(AlertService, '__init__', initialize)
    response = client.post('/api/notify/send', json={'message': 'Lab opens at 9 AM.'}, headers=admin)
    assert response.status_code == 200 and response.json()['telegram_sent'] is False
    with _db.get_connection() as conn:
        conn.execute("UPDATE alerts SET last_attempt_at=datetime('now','-2 minutes')")
    result = client.post('/api/notify/retry', headers=admin)
    assert result.json()['delivered'] == 1
    history = client.get('/api/notify/history', headers=admin).json()['notifications'][0]
    assert history['sent_status'] == 'sent' and history['delivery_attempts'] == 2 and history['last_error'] is None


def test_queue_deduplicates_and_claims_once(showcase):
    _client, _admin, _member, _db = showcase
    service = object.__new__(AlertService)
    service.enabled = True
    service.bot = object()
    calls = []
    async def send(*args):
        calls.append(args)
        await asyncio.sleep(0)
        return True, 'sent'
    service._send = send
    first = service.save_alert_to_db('REPORT', 'Daily summary', severity='low', dedupe_key='daily:2026-10-14')
    second = service.save_alert_to_db('REPORT', 'Daily summary', severity='low', dedupe_key='daily:2026-10-14')
    assert first == second
    async def compete():
        return await asyncio.gather(service.deliver(first), service.deliver(second))
    asyncio.run(compete())
    assert len(calls) == 1


def test_real_telegram_sdk_transport_contract(showcase, monkeypatch):
    """Exercise SDK response parsing without sending to a real group."""
    from telegram import Bot as RealBot
    from telegram.request import BaseRequest
    import telegram
    import app.alerts as alerts
    deliveries = []
    class TelegramRequest(BaseRequest):
        @property
        def read_timeout(self): return 5
        async def initialize(self): pass
        async def shutdown(self): pass
        async def do_request(self, url, method, request_data=None, **kwargs):
            endpoint = url.rsplit('/', 1)[-1]
            if endpoint == 'getMe': result = {'id': 123456, 'is_bot': True, 'first_name': 'AAMS Test Bot'}
            elif endpoint == 'sendMessage':
                deliveries.append(request_data.parameters['text'])
                result = {'message_id': 1, 'date': 1, 'chat': {'id': -100123, 'type': 'supergroup', 'title': 'AAMS Test Group'}, 'text': deliveries[-1]}
            elif endpoint == 'getChat': result = {'id': -100123, 'type': 'supergroup', 'title': 'AAMS Test Group', 'accent_color_id': 1, 'max_reaction_count': 0}
            else: raise AssertionError(endpoint)
            return 200, json.dumps({'ok': True, 'result': result}).encode()
    monkeypatch.setattr(telegram, 'Bot', lambda token, request: RealBot(token=token, request=TelegramRequest(), get_updates_request=TelegramRequest()))
    monkeypatch.setattr(alerts, 'get_telegram_config', lambda: {'enabled': True, 'bot_token': '123456:' + 'a' * 30, 'chat_id': '-100123'})
    client, admin, _member, _db = showcase
    response = client.post('/api/notify/test', headers=admin)
    assert response.status_code == 200 and response.json()['telegram_sent'] is True
    assert len(deliveries) == 1 and 'AAMS connection test' in deliveries[0]
    assert client.post('/api/notify/verify', headers=admin).json()['group_title'] == 'AAMS Test Group'


def test_daily_report_includes_sqlite_timestamps_and_ist_boundaries(showcase):
    _client, _admin, _member, db = showcase
    with db.get_connection() as conn:
        for stamp in ('2026-10-13 19:00:00', '2026-10-14T04:00:00', '2026-10-14 19:00:00'):
            conn.execute("INSERT INTO entry_logs(event_time, recognized_id, tag, decision) VALUES (?, 'TEST', 'authorized', 'GRANTED')", (stamp,))
    from app.reports import ReportGenerator
    report = ReportGenerator().generate_daily('2026-10-14')
    assert report['total_entries'] == 2 and report['authorized'] == 2


def test_sqlite_wal_backup_preserves_committed_rows(showcase, tmp_path):
    _client, _admin, _member, db = showcase
    from app.scheduler import ReportScheduler
    source = db.get_connection()
    source.execute("INSERT INTO users(user_id,name,email) VALUES('BACKUP','Backup Student','backup@srmist.edu.in')")
    source.commit()
    ReportScheduler(None, None, db.DATABASE_PATH).backup_database()
    import sqlite3
    backup = next(tmp_path.glob('*.backup.*'))
    with sqlite3.connect(backup) as restored:
        assert restored.execute("SELECT name FROM users WHERE user_id='BACKUP'").fetchone()[0] == 'Backup Student'
    source.close()


def test_signed_qr_entry_matches_enrolled_student_and_enforces_expiry(showcase, monkeypatch):
    client, admin, _member, db = showcase
    import numpy as np
    import app.vision as vision
    from app.qr_manager import QRManager
    vector = np.arange(512, dtype=np.float64) + 1
    vector /= np.linalg.norm(vector)
    monkeypatch.setattr(vision, 'decode_image', lambda _payload: np.zeros((240, 240, 3), dtype=np.uint8))
    monkeypatch.setattr(vision, 'analyze_frame', lambda _frame: {'face_count': 1, 'quality_passed': True, 'quality_reasons': [], 'embedding': vector})
    monkeypatch.setattr(vision, 'save_evidence', lambda *_args: None)
    client.post('/api/users', headers=admin, json=student_payload())
    qr = QRManager()
    token = qr.generate_token('STUDENT-001')
    with db.get_connection() as conn:
        conn.execute('UPDATE users SET face_embedding=? WHERE user_id=?', (vector.tobytes(), 'STUDENT-001'))
        conn.execute('INSERT INTO tokens(token_value,user_id) VALUES(?,?)', (qr.serialize_token(token), 'STUDENT-001'))
    payload = {'image_b64': 'fixture-photo', 'token_value': json.dumps(token), 'skip_liveness': True}
    granted = client.post('/api/entry/process', headers=admin, json=payload)
    assert granted.status_code == 200 and granted.json()['decision'] == 'GRANTED'
    assert granted.json()['occupant_state'] == 'inside'
    with db.get_connection() as conn:
        log = conn.execute('SELECT claimed_id FROM entry_logs').fetchone()[0]
        assert log == 'STUDENT-001', 'Signed bearer pass must not leak into logs'
    client.put('/api/users/STUDENT-001', headers=admin, json={'payment_expiry': '2020-01-01'})
    denied = client.post('/api/entry/process', headers=admin, json=payload)
    assert denied.json()['decision'] == 'DENIED' and denied.json()['tag'] == 'unpaid'
    client.post('/api/users/STUDENT-001/tokens/revoke', headers=admin)
    assert client.post('/api/entry/process', headers=admin, json=payload).json()['decision'] == 'DENIED'


@pytest.mark.parametrize('token', ['[]', 'null', '123', '{"user_id":"T","token_id":"id","issued_at":"bad","expires_at":"bad","signature":0}'])
def test_malformed_signed_pass_is_rejected_without_exception(token):
    from app.qr_manager import QRManager
    assert QRManager().verify_token(token)['valid'] is False


def test_pose_gate_uses_insightface_pitch_yaw_order():
    import numpy as np
    from types import SimpleNamespace
    from app.face_engine import FaceEngine
    engine = object.__new__(FaceEngine)
    engine.min_face_size = 0
    engine.blur_threshold = 0
    engine.brightness_min = 0
    engine.brightness_max = 255
    engine.max_pitch = 20
    engine.max_yaw = 25
    engine.max_roll = 20
    face = SimpleNamespace(bbox=np.array([0, 0, 100, 100]), pose=np.array([22.0, 0.0, 0.0]))
    passed, reasons = engine.quality_check(face, np.zeros((100, 100, 3), dtype=np.uint8))
    assert not passed and any('Pitch' in reason for reason in reasons)


def test_background_camera_queues_notifications_and_blocks_expired_payment(showcase, monkeypatch):
    client, admin, _member, db = showcase
    import numpy as np
    import app.utils as utils
    from app.capture_service import CaptureService
    monkeypatch.setattr(utils, 'save_frame', lambda *_args, **_kwargs: None)
    client.post('/api/users', headers=admin, json=student_payload())
    capture = CaptureService()
    student = {**student_payload(), 'payment_expiry': '2020-01-01'}
    capture._record_entry(student, {'similarity': 0.99}, np.zeros((200, 200, 3), dtype=np.uint8))
    assert capture.last_event['decision'] == 'DENIED'
    with db.get_connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM alerts WHERE alert_type='UNPAID' AND sent_status='pending'").fetchone()[0] == 1


def test_liveness_requirement_applies_to_multiple_faces():
    from app.access_policy import AccessDecision
    result = AccessDecision(require_liveness=True).evaluate_access('TEST', {'result': 'MATCH'}, 'active', 'unknown', 2)
    assert result['decision'] == 'DENIED'


def test_disabled_student_session_is_rejected(showcase):
    client, admin, member, db = showcase
    client.post('/api/users', headers=admin, json={**student_payload(), 'email': 'member@srmist.edu.in'})
    assert client.put('/api/users/STUDENT-001', headers=admin, json={'active': 0}).status_code == 200
    assert client.get('/api/users', headers=member).status_code == 401


def test_student_notifications_do_not_count_as_security_incidents(showcase):
    client, admin, _member, _db = showcase
    client.post('/api/users', headers=admin, json=student_payload())
    assert client.get('/api/dashboard/stats', headers=admin).json()['alert_count'] == 0
    assert client.get('/api/alerts', headers=admin).json()['alerts'] == []
    assert client.get('/api/notify/history', headers=admin).json()['notifications'][0]['alert_type'] == 'ENROLLMENT'
