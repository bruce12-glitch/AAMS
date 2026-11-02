"""Telegram flood waits and uncertain outcomes use a durable retry, not spam."""
import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest
from telegram.error import BadRequest, Forbidden, NetworkError, RetryAfter, TimedOut

from app.alerts import AlertService
from tests.test_showcase_flows import showcase


def service_with_bot():
    service = object.__new__(AlertService)
    service.enabled, service.send_photo, service.chat_id = True, True, '123456'
    service.bot = AsyncMock()
    service.bot.__aenter__.return_value = service.bot
    return service


@pytest.mark.parametrize('error', [TimedOut('private URL hidden'), NetworkError('private URL hidden'),
                                  Forbidden('private URL hidden'), RetryAfter(121)])
def test_uncertain_photo_send_does_not_fall_back_or_leak(error, tmp_path, monkeypatch, caplog):
    import app.alerts as alerts
    monkeypatch.setattr(alerts, 'BASE_DIR', tmp_path)
    (tmp_path / 'images').mkdir()
    (tmp_path / 'images' / 'evidence.jpg').write_bytes(b'fixture')
    service = service_with_bot()
    service.bot.send_photo.side_effect = error
    sent, reason = asyncio.run(service._send('Attendance message', 'images/evidence.jpg'))
    assert not sent and 'private URL' not in reason and 'private URL' not in caplog.text
    service.bot.send_photo.assert_awaited_once()
    service.bot.send_message.assert_not_awaited()


def test_rejected_photo_can_fall_back_once_and_long_caption_is_one_delivery(tmp_path, monkeypatch):
    import app.alerts as alerts
    monkeypatch.setattr(alerts, 'BASE_DIR', tmp_path)
    (tmp_path / 'images').mkdir()
    (tmp_path / 'images' / 'evidence.jpg').write_bytes(b'fixture')
    service = service_with_bot()
    service.bot.send_photo.side_effect = BadRequest('Photo invalid')
    assert asyncio.run(service._send('Attendance', 'images/evidence.jpg'))[0]
    service.bot.send_message.assert_awaited_once()
    service = service_with_bot()
    assert asyncio.run(service._send('x' * 2000, 'images/evidence.jpg'))[0]
    caption = service.bot.send_photo.await_args.kwargs['caption']
    assert len(caption) <= 1024 and 'Full message in AAMS' in caption
    service.bot.send_message.assert_not_awaited()


@pytest.mark.parametrize('retry_after', [121, timedelta(seconds=121)])
def test_rate_limit_is_persisted_across_restart_and_pauses_existing_queue(showcase, retry_after):
    _client, _admin, _member, db = showcase
    service = service_with_bot()
    first = service.save_alert_to_db('ENTRY', 'First entry', severity='low')
    second = service.save_alert_to_db('ENTRY', 'Second entry', severity='low')
    service.bot.send_message.side_effect = RetryAfter(retry_after)
    before = datetime.now(timezone.utc)
    assert asyncio.run(service.flush_pending()) == 0
    service.bot.send_message.assert_awaited_once()
    with db.get_connection() as conn:
        rows = conn.execute('SELECT * FROM alerts ORDER BY id').fetchall()
    assert rows[0]['sent_status'] == rows[1]['sent_status'] == 'pending'
    assert rows[0]['delivery_attempts'] == 1 and rows[1]['delivery_attempts'] == 0
    assert datetime.fromisoformat(rows[0]['next_attempt_at']) >= before + timedelta(seconds=121)
    assert rows[0]['next_attempt_at'] == rows[1]['next_attempt_at']
    restarted = service_with_bot()
    third = restarted.save_alert_to_db('ENTRY', 'New entry during flood wait', severity='low')
    assert not asyncio.run(restarted.deliver(third))[0]
    assert asyncio.run(restarted.flush_pending()) == 0
    assert not asyncio.run(restarted.deliver(first))[0]
    restarted.bot.send_message.assert_not_awaited()
    with db.get_connection() as conn:
        conn.execute("UPDATE alerts SET last_attempt_at=datetime('now','-3 minutes'), next_attempt_at=datetime('now','-1 second')")
    assert asyncio.run(restarted.flush_pending()) == 3
    assert restarted.bot.send_message.await_count == 3
    assert asyncio.run(restarted.deliver(second))[0]
    assert restarted.bot.send_message.await_count == 3, 'Delivered events must not be sent again'


def test_network_retry_backoff_increases_and_history_is_private(showcase, monkeypatch):
    client, admin, member, db = showcase
    service = service_with_bot()
    service.bot.send_message.side_effect = NetworkError('private URL hidden')
    alert_id = service.save_alert_to_db('ENTRY', 'Attendance', severity='low')
    for attempt in range(1, 4):
        before = datetime.now(timezone.utc)
        assert not asyncio.run(service.deliver(alert_id))[0]
        with db.get_connection() as conn:
            row = conn.execute('SELECT * FROM alerts WHERE id=?', (alert_id,)).fetchone()
            assert row['delivery_attempts'] == attempt
            assert datetime.fromisoformat(row['next_attempt_at']) >= before + timedelta(seconds=60 * 2 ** (attempt - 1))
            conn.execute("UPDATE alerts SET next_attempt_at=datetime('now','-1 second') WHERE id=?", (alert_id,))
    history = client.get('/api/notify/history', headers=admin)
    assert history.status_code == 200 and 'next_attempt_at' in history.json()['notifications'][0]
    assert 'private URL' not in history.text
    assert client.get('/api/notify/history', headers=member).status_code == 403
