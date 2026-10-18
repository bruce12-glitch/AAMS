"""Continuous camera attendance must not flood records or Telegram."""
import asyncio
from unittest.mock import AsyncMock

import numpy as np

from api.routes_entry import EntryRequest, _finalize, _run_pipeline


def test_continuous_empty_camera_does_not_store_or_notify(tmp_path, monkeypatch):
    import app.database as db
    import app.vision as vision
    monkeypatch.setattr(db, 'DATABASE_PATH', tmp_path / 'empty.db')
    db.init_db()
    monkeypatch.setattr(vision, 'decode_image', lambda _: np.zeros((240, 240, 3)))
    monkeypatch.setattr(vision, 'analyze_frame', lambda _: {'face_count': 0})
    monkeypatch.setattr(vision, 'save_evidence', lambda *_: (_ for _ in ()).throw(AssertionError('empty frame saved')))
    response = asyncio.run(_run_pipeline(EntryRequest(image_b64='frame', continuous=True), 'face_only'))
    assert response['recorded'] is False
    conn = db.get_connection()
    assert conn.execute('SELECT COUNT(*) FROM entry_logs').fetchone()[0] == 0
    conn.close()


def test_continuous_grant_notifies_once_until_checkout(tmp_path, monkeypatch):
    import app.database as db
    from app.alerts import AlertService
    from app.occupancy import OccupancyTracker
    monkeypatch.setattr(db, 'DATABASE_PATH', tmp_path / 'entry.db')
    db.init_db()
    conn = db.get_connection()
    conn.execute("INSERT INTO users (user_id, name, email) VALUES ('CAM-1', 'Camera Student', 'cam@srmist.edu.in')")
    conn.commit()
    conn.close()
    notify = AsyncMock(return_value={'alert_id': 1})
    monkeypatch.setattr(AlertService, 'queue_and_deliver', notify)
    payload = dict(decision='GRANTED', reason='Face matched', tag='authorized', alert_type=None,
                   user={'user_id': 'CAM-1', 'name': 'Camera Student', 'payment_status': 'active'},
                   similarity=.9, liveness_status='real', claimed='CAM-1', evidence=None,
                   extra={'recognized_id': 'CAM-1', 'continuous': True})
    first = asyncio.run(_finalize(**payload))
    second = asyncio.run(_finalize(**payload))
    assert first['recorded'] is True and second['duplicate'] is True
    assert notify.await_count == 1
    conn = db.get_connection()
    assert conn.execute('SELECT COUNT(*) FROM entry_logs').fetchone()[0] == 1
    conn.close()
    OccupancyTracker().mark_exit('CAM-1')
    assert asyncio.run(_finalize(**payload))['recorded'] is True
    assert notify.await_count == 2


def test_continuous_denials_are_throttled(tmp_path, monkeypatch):
    import app.database as db
    from app.alerts import AlertService
    monkeypatch.setattr(db, 'DATABASE_PATH', tmp_path / 'denial.db')
    db.init_db()
    notify = AsyncMock(return_value={'alert_id': 1})
    monkeypatch.setattr(AlertService, 'queue_and_deliver', notify)
    payload = dict(decision='DENIED', reason='Unknown face', tag='unknown', alert_type='UNKNOWN',
                   user=None, similarity=0, liveness_status='real', claimed=None,
                   evidence=None, extra={'continuous': True})
    assert asyncio.run(_finalize(**payload))['recorded'] is True
    assert asyncio.run(_finalize(**payload))['duplicate'] is True
    assert notify.await_count == 1


def test_continuous_scan_requires_liveness_unless_explicitly_bypassed(tmp_path, monkeypatch):
    import app.database as db
    import app.vision as vision
    from app.identity import IdentityVerifier
    from app.alerts import AlertService
    monkeypatch.setattr(db, 'DATABASE_PATH', tmp_path / 'liveness.db')
    db.init_db()
    monkeypatch.setattr(vision, 'decode_image', lambda _: np.zeros((240, 240, 3)))
    monkeypatch.setattr(vision, 'analyze_frame', lambda _: {
        'face_count': 1, 'quality_passed': True, 'embedding': np.ones(512)})
    monkeypatch.setattr(vision, 'save_evidence', lambda *_: None)
    monkeypatch.setattr(IdentityVerifier, 'verify_face_only', lambda *_: {
        'result': 'MATCH', 'match': True, 'similarity': .95,
        'user': {'user_id': 'LIVE-1', 'name': 'Student', 'payment_status': 'active'}})
    monkeypatch.setattr(AlertService, 'queue_and_deliver', AsyncMock(return_value={'alert_id': 1}))
    result = asyncio.run(_run_pipeline(EntryRequest(image_b64='frame', continuous=True), 'face_only'))
    assert result['decision'] == 'DENIED'
    assert result['reason'].startswith('Liveness not verified')
