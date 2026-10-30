"""Records must distinguish capture decisions, historical data and demo fixtures."""
import asyncio
import sqlite3
from unittest.mock import AsyncMock

import numpy as np
import pytest

from tests.test_showcase_flows import showcase, student_payload


def test_migration_preserves_unlabelled_history(tmp_path, monkeypatch):
    import app.database as db
    monkeypatch.setattr(db, 'DATABASE_PATH', tmp_path / 'legacy.db')
    with sqlite3.connect(db.DATABASE_PATH) as conn:
        conn.execute('CREATE TABLE entry_logs(id INTEGER PRIMARY KEY, reason TEXT)')
        conn.execute("INSERT INTO entry_logs(reason) VALUES ('Original legacy record')")
        conn.execute('CREATE TABLE alerts(id INTEGER PRIMARY KEY, message TEXT)')
        conn.execute("INSERT INTO alerts(message) VALUES ('Original historical message')")
    db.init_db()
    db.init_db()
    with db.get_connection() as conn:
        event = conn.execute('SELECT * FROM entry_logs').fetchone()
        assert event['reason'] == 'Original legacy record' and event['event_source'] == 'legacy'
        assert event['comparison_performed'] is None
        assert conn.execute('SELECT event_source FROM alerts').fetchone()[0] == 'legacy'


def test_views_separate_history_and_link_recorded_alerts(showcase):
    client, admin, _member, db = showcase
    with db.get_connection() as conn:
        conn.execute("INSERT INTO users(user_id,name,email) VALUES ('REAL','Real Member','real@srmist.edu.in')")
        for source in ('legacy', 'sample', 'webcam'):
            event = conn.execute("INSERT INTO entry_logs(recognized_id,decision,reason,tag,event_source,comparison_performed,similarity) VALUES ('REAL','DENIED','Payment expired','unpaid',?,1,.85)", (source,)).lastrowid
            conn.execute("INSERT INTO alerts(alert_type,message,event_source,entry_log_id) VALUES ('UNPAID','Stored message',?,?)", (source, event))
    current = client.get('/api/dashboard/activity?scope=recorded', headers=admin).json()
    assert len(current['activities']) == 1 and current['activities'][0]['recognized_name'] == 'Real Member'
    assert current['source_counts'] == {'legacy': 1, 'sample': 1, 'webcam': 1}
    assert len(client.get('/api/dashboard/activity?scope=history', headers=admin).json()['activities']) == 2
    assert len(client.get('/api/dashboard/activity?scope=all', headers=admin).json()['activities']) == 3
    alerts = client.get('/api/alerts?scope=recorded&status=open', headers=admin).json()['alerts']
    assert len(alerts) == 1 and alerts[0]['decision_reason'] == 'Payment expired'
    assert alerts[0]['recognized_name'] == 'Real Member' and alerts[0]['entry_log_id']
    assert client.post(f'/api/alerts/{alerts[0]["id"]}/ack', headers=admin).status_code == 200
    assert client.get('/api/alerts?scope=recorded&status=open', headers=admin).json()['alerts'] == []
    assert len(client.get('/api/alerts?scope=recorded&status=reviewed', headers=admin).json()['alerts']) == 1
    assert client.get('/api/dashboard/activity?scope=invalid', headers=admin).status_code == 422


@pytest.mark.parametrize('case,expected', [('noface', 'noface'), ('quality', 'quality'), ('token', 'token')])
def test_routine_capture_errors_do_not_generate_security_incidents(showcase, monkeypatch, case, expected):
    import app.vision as vision
    import app.notification_settings as settings
    client, admin, _member, db = showcase
    settings.save_settings({'enabled': False})
    vector = np.zeros(512)
    vector[0] = 1
    monkeypatch.setattr(vision, 'decode_image', lambda _: np.zeros((240, 240, 3), dtype=np.uint8))
    monkeypatch.setattr(vision, 'save_evidence', lambda *_: None)
    monkeypatch.setattr(vision, 'analyze_frame', lambda _: {'face_count': 0 if case == 'noface' else 1,
        'quality_passed': case == 'token', 'quality_reasons': ['Face too blurry'], 'embedding': vector})
    path = '/api/entry/process' if case == 'token' else '/api/entry/face-only'
    response = client.post(path, headers=admin, json={'image_b64': 'fixture', 'token_value': 'invalid-id', 'skip_liveness': True})
    assert response.status_code == 200, response.text
    assert response.json()['decision'] == 'DENIED' and response.json()['tag'] == expected
    with db.get_connection() as conn:
        assert conn.execute('SELECT COUNT(*) FROM alerts').fetchone()[0] == 0
        event = conn.execute('SELECT * FROM entry_logs').fetchone()
        assert event['event_source'] == 'snapshot' and event['comparison_performed'] == 0


def test_real_unknown_comparison_has_a_linked_capture(showcase, monkeypatch):
    import app.vision as vision
    import app.notification_settings as settings
    client, admin, _member, db = showcase
    settings.save_settings({'enabled': False})
    vector = np.zeros(512)
    vector[0] = 1
    with db.get_connection() as conn:
        conn.execute("INSERT INTO users(user_id,name,email,face_embedding) VALUES ('REAL','Real Member','real@srmist.edu.in',?)", (np.roll(vector, 1).tobytes(),))
    monkeypatch.setattr(vision, 'decode_image', lambda _: np.zeros((240, 240, 3), dtype=np.uint8))
    monkeypatch.setattr(vision, 'save_evidence', lambda *_: None)
    monkeypatch.setattr(vision, 'analyze_frame', lambda _: {'face_count': 1, 'quality_passed': True, 'quality_reasons': [], 'embedding': vector})
    response = client.post('/api/entry/face-only', headers=admin, json={'image_b64': 'fixture', 'capture_source': 'webcam', 'skip_liveness': True})
    assert response.status_code == 200, response.text
    alert = client.get('/api/alerts?scope=recorded', headers=admin).json()['alerts'][0]
    assert alert['event_source'] == 'webcam' and alert['entry_log_id'] == response.json()['id']
    assert alert['comparison_performed'] == 1 and alert['alert_type'] == 'UNKNOWN'


def test_denials_and_samples_are_not_counted_as_attendance(showcase):
    from app.reports import ReportGenerator
    client, admin, _member, db = showcase
    with db.get_connection() as conn:
        for decision, source, recognized in [('GRANTED', 'webcam', 'REAL'), ('DENIED', 'webcam', 'DENIED-ID'), ('GRANTED', 'sample', 'DEMO')]:
            conn.execute("INSERT INTO entry_logs(recognized_id,decision,tag,event_source) VALUES (?,?,?,?)", (recognized, decision, 'authorized' if decision == 'GRANTED' else 'unpaid', source))
    assert client.get('/api/dashboard/stats?scope=recorded', headers=admin).json()['total_entries'] == 1
    daily = ReportGenerator().generate_daily()
    assert daily['total_entries'] == 1 and daily['unique_users'] == 1 and daily['unpaid_attempts'] == 1


def test_member_cannot_edit_status_and_admin_changes_preserve_biometrics(showcase):
    from app.occupancy import OccupancyTracker
    import app.notification_settings as settings
    client, admin, member, db = showcase
    settings.save_settings({'notify_on_enrollment': False})
    assert client.post('/api/users', headers=admin, json=student_payload()).status_code == 200
    assert client.post('/api/users/STUDENT-001/tokens/revoke', headers=admin).status_code == 200
    vector = np.ones(512).tobytes()
    with db.get_connection() as conn:
        conn.execute("UPDATE users SET face_embedding=? WHERE user_id='STUDENT-001'", (vector,))
    OccupancyTracker().mark_inside('STUDENT-001')
    assert client.put('/api/users/STUDENT-001', headers=member, json={'active': 0, 'payment_status': 'expired'}).status_code == 403
    assert client.put('/api/users/STUDENT-001', headers=admin, json={'payment_status': 'pending'}).status_code == 200
    assert client.put('/api/users/STUDENT-001', headers=admin, json={'active': 0}).status_code == 200
    with db.get_connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE user_id='STUDENT-001'").fetchone()
        assert row['face_embedding'] == vector and row['active'] == 0 and row['payment_status'] == 'pending'
        assert conn.execute("SELECT COUNT(*) FROM occupants WHERE status='inside'").fetchone()[0] == 0
        assert conn.execute('SELECT COUNT(*) FROM tokens WHERE active=1').fetchone()[0] == 0
    assert client.put('/api/users/STUDENT-001', headers=admin, json={'active': 1}).status_code == 200
    with db.get_connection() as conn:
        assert conn.execute('SELECT COUNT(*) FROM tokens WHERE active=1').fetchone()[0] == 0


def test_seed_is_blocked_in_production_and_preserves_existing_records(showcase, monkeypatch):
    from scripts.seed_demo_data import main
    client, admin, _member, db = showcase
    monkeypatch.setenv('AAMS_ENV', 'production')
    with pytest.raises(RuntimeError, match='disabled in production'):
        main()
    monkeypatch.setenv('AAMS_ENV', 'development')
    client.post('/api/users', headers=admin, json=student_payload())
    with pytest.raises(RuntimeError, match='non-empty'):
        main()
    with db.get_connection() as conn:
        assert conn.execute('SELECT user_id FROM users').fetchone()[0] == 'STUDENT-001'


def test_samples_have_no_fake_biometrics_or_delivery(showcase, monkeypatch):
    from scripts.seed_demo_data import main
    from app.alerts import AlertService
    client, admin, _member, db = showcase
    monkeypatch.setenv('AAMS_ENV', 'development')
    main()
    with db.get_connection() as conn:
        assert conn.execute('SELECT COUNT(*) FROM users WHERE face_embedding IS NOT NULL OR active=1').fetchone()[0] == 0
        assert conn.execute('SELECT COUNT(*) FROM occupants').fetchone()[0] == 0
        alert_id = conn.execute('SELECT id FROM alerts LIMIT 1').fetchone()[0]
        conn.execute("UPDATE alerts SET sent_status='pending'")
    service = object.__new__(AlertService)
    service.enabled, service.bot = True, object()
    service._send = AsyncMock()
    assert asyncio.run(service.deliver(alert_id))[0] is False
    assert asyncio.run(service.flush_pending()) == 0
    service._send.assert_not_awaited()
    assert client.get('/api/alerts?scope=recorded', headers=admin).json()['alerts'] == []
    assert client.get('/api/dashboard/stats?scope=recorded', headers=admin).json()['total_entries'] == 0
