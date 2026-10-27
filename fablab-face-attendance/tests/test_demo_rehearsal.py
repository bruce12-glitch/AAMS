"""Final-demo checks use disposable data and never contact a real Telegram chat."""
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock
from zoneinfo import ZoneInfo

import pytest

from tests.test_showcase_flows import showcase, student_payload


def test_scheduler_does_not_depend_on_computer_timezone(monkeypatch):
    import apscheduler.triggers.interval as interval
    from app.scheduler import ReportScheduler

    def unavailable_timezone():
        raise AssertionError('The host timezone must not be queried')

    monkeypatch.setattr(interval, 'get_localzone', unavailable_timezone)
    scheduler = ReportScheduler(None, None)
    for job in scheduler.scheduler.get_jobs():
        assert str(job.trigger.timezone) == 'Asia/Kolkata'


def test_readiness_distinguishes_enrolled_from_entry_eligible(showcase):
    client, admin, _member, db = showcase
    today = datetime.now(ZoneInfo('Asia/Kolkata')).date()
    with db.get_connection() as conn:
        rows = [
            ('CURRENT', 'active', today.isoformat(), 1, b'face'),
            ('NO-EXPIRY', 'active', None, 1, b'face'),
            ('PAST', 'active', (today - timedelta(days=1)).isoformat(), 1, b'face'),
            ('PENDING', 'pending', None, 1, b'face'),
            ('INVALID', 'active', 'not-a-date', 1, b'face'),
            ('DISABLED', 'active', None, 0, b'face'),
            ('NO-FACE', 'active', None, 1, None),
        ]
        conn.executemany('INSERT INTO users(user_id,name,payment_status,payment_expiry,active,face_embedding_2) VALUES (?, ?, ?, ?, ?, ?)',
                         [(uid, uid, payment, expiry, active, face) for uid, payment, expiry, active, face in rows])
        conn.execute("INSERT INTO alerts(alert_type,message,sent_status) VALUES ('ENTRY','Queued test','pending')")
    result = client.get('/api/admin/readiness', headers=admin).json()
    assert result['active_members'] == 6
    assert result['enrolled_members'] == 5
    assert result['eligible_members'] == 2
    assert result['telegram']['pending_count'] == 1
    assert result['telegram']['notify_on_entry'] is True
    client.put('/api/notify/settings', json={'enabled': False, 'notify_on_entry': False}, headers=admin)
    assert client.get('/api/admin/readiness', headers=admin).json()['telegram']['notify_on_entry'] is False


@pytest.mark.parametrize('sent', [True, False])
def test_automatic_entry_reports_delivery_without_repeat_spam(showcase, monkeypatch, sent):
    from api.routes_entry import _finalize
    from app.alerts import AlertService

    client, admin, _member, db = showcase
    # Do not create real or persistent sample users: the fixture owns this DB.
    client.put('/api/notify/settings', json={'enabled': False, 'notify_on_enrollment': False}, headers=admin)
    student = student_payload()
    assert client.post('/api/users', json=student, headers=admin).status_code == 200
    notify = AsyncMock(return_value={'alert_id': 77, 'telegram_sent': sent,
                                    'reason': 'Delivered to Telegram' if sent else 'Telegram is unreachable; the message remains queued for retry.'})
    monkeypatch.setattr(AlertService, 'queue_and_deliver', notify)
    payload = dict(decision='GRANTED', reason='Face matched', tag='authorized', alert_type=None,
                   user=student, similarity=.95, liveness_status='real', claimed=student['user_id'],
                   evidence=None, extra={'continuous': True, 'recognized_id': student['user_id']})
    first = asyncio.run(_finalize(**payload))
    assert first['notification']['status'] == ('sent' if sent else 'queued')
    assert first['notification']['telegram_sent'] is sent
    message = notify.await_args.args[1]
    assert student['name'] in message and student['user_id'] in message and 'IST' in message
    repeat = asyncio.run(_finalize(**payload))
    assert repeat['duplicate'] is True and repeat['recorded'] is False
    assert 'notification' not in repeat  # Do not claim a new message was sent.
    assert notify.await_count == 1
    with db.get_connection() as conn:
        assert conn.execute('SELECT COUNT(*) FROM entry_logs').fetchone()[0] == 1
    client.post(f"/api/occupants/{student['user_id']}/exit", headers=admin)
    assert asyncio.run(_finalize(**payload))['recorded'] is True
    assert notify.await_count == 2


def test_entry_notification_off_is_explicit_and_does_not_send(showcase, monkeypatch):
    from api.routes_entry import _finalize
    from app.alerts import AlertService

    client, admin, _member, _db = showcase
    client.put('/api/notify/settings', json={'enabled': False, 'notify_on_enrollment': False, 'notify_on_entry': False}, headers=admin)
    student = student_payload()
    client.post('/api/users', json=student, headers=admin)
    notify = AsyncMock()
    monkeypatch.setattr(AlertService, 'queue_and_deliver', notify)
    result = asyncio.run(_finalize(
        decision='GRANTED', reason='Face matched', tag='authorized', alert_type=None,
        user=student, similarity=.95, liveness_status='real', claimed=student['user_id'],
        evidence=None, extra={'continuous': True, 'recognized_id': student['user_id']}))
    assert result['recorded'] is True and result['notification']['status'] == 'disabled'
    notify.assert_not_awaited()


def test_duplicate_ids_and_emails_do_not_create_extra_students_or_notifications(showcase):
    client, admin, _member, db = showcase
    client.put('/api/notify/settings', json={'enabled': False}, headers=admin)
    student = student_payload()
    assert client.post('/api/users', json=student, headers=admin).status_code == 200
    assert client.post('/api/users', json={**student, 'email': 'different@srmist.edu.in'}, headers=admin).status_code == 409
    assert client.post('/api/users', json={**student, 'user_id': 'OTHER-ID', 'email': student['email'].upper()}, headers=admin).status_code == 409
    with db.get_connection() as conn:
        assert conn.execute('SELECT COUNT(*) FROM users').fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM alerts WHERE alert_type='ENROLLMENT'").fetchone()[0] == 1
