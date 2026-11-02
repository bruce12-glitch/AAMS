"""Regression tests for searchable history and honest, non-destructive examples."""
import numpy as np
import pytest

from tests.test_showcase_flows import showcase, student_payload


def test_search_scans_entire_database_and_matches_names_ids_and_reasons(showcase):
    client, admin, _member, db = showcase
    with db.get_connection() as conn:
        conn.execute("INSERT INTO users(user_id,name) VALUES ('RA_123','Rahul Kumar')")
        conn.execute("INSERT INTO entry_logs(recognized_id,decision,reason,event_source) VALUES ('RA_123','GRANTED','Original permitted entry','legacy')")
        conn.execute("INSERT INTO entry_logs(claimed_id,decision,reason,event_source) VALUES ('RA_123','DENIED','Payment pending','webcam')")
        conn.executemany("INSERT INTO entry_logs(decision,reason,event_source) VALUES ('DENIED',?,'webcam')", [(f'Recent unrelated {i}',) for i in range(520)])
    for term, total in [('rahul', 2), ('RA_123', 2), ('permitted', 1), ('payment', 1)]:
        response = client.get('/api/dashboard/activity', headers=admin, params={'q': term, 'scope': 'all'})
        assert response.status_code == 200, response.text
        assert response.json()['total'] == total
        assert len(response.json()['activities']) == total
    granted = client.get('/api/dashboard/activity', headers=admin, params={'q': 'Rahul', 'decision': 'GRANTED'}).json()
    assert granted['total'] == 1 and granted['activities'][0]['event_source'] == 'legacy'
    assert client.get('/api/dashboard/activity?q=rahul&scope=recorded', headers=admin).json()['total'] == 1
    for term in ('%', 'RA_999', "' OR 1=1 --"):
        assert client.get('/api/dashboard/activity', headers=admin, params={'q': term}).json()['total'] == 0
    first = client.get('/api/dashboard/activity?limit=50', headers=admin).json()
    second = client.get('/api/dashboard/activity?limit=50&offset=50', headers=admin).json()
    assert first['total'] == 522 and len(first['activities']) == 50
    assert not ({r['id'] for r in first['activities']} & {r['id'] for r in second['activities']})
    for params in ({'decision': 'INVALID'}, {'offset': -1}, {'q': 'a' * 201}):
        assert client.get('/api/dashboard/activity', headers=admin, params=params).status_code == 422


def test_demo_examples_are_admin_only_idempotent_and_have_no_biometrics_or_notifications(showcase, monkeypatch):
    from app.alerts import AlertService
    from app.identity import IdentityVerifier
    from app.reports import ReportGenerator
    client, admin, member, db = showcase
    monkeypatch.setenv('AAMS_ENV', 'production')
    monkeypatch.setattr(AlertService, 'queue_and_deliver', lambda *a, **k: pytest.fail('Demo examples notified someone'))
    assert client.post('/api/admin/demo-data').status_code == 401
    assert client.post('/api/admin/demo-data', headers=member).status_code == 403
    first = client.post('/api/admin/demo-data', headers=admin)
    assert first.status_code == 200, first.text
    assert first.json()['members_created'] == 6 and first.json()['examples_created'] == 6
    again = client.post('/api/admin/demo-data', headers=admin).json()
    assert again['members_created'] == 0 and again['examples_created'] == 0
    users = client.get('/api/users', headers=admin).json()['users']
    assert all(not row['enrolled'] and row['is_demo'] == 1 and not row['email'] for row in users)
    assert IdentityVerifier().get_all_user_embeddings() == {}
    with db.get_connection() as conn:
        assert conn.execute('SELECT COUNT(*) FROM occupants').fetchone()[0] == 0
        assert conn.execute('SELECT COUNT(*) FROM alerts').fetchone()[0] == 0
        assert conn.execute('SELECT COUNT(*) FROM tokens').fetchone()[0] == 0
        assert conn.execute('SELECT COUNT(*) FROM entry_logs WHERE similarity IS NOT NULL OR comparison_performed<>0').fetchone()[0] == 0
    stats = client.get('/api/dashboard/stats?scope=recorded', headers=admin).json()
    assert stats['total_entries'] == 0 and stats['member_count'] == 0
    ready = client.get('/api/admin/readiness', headers=admin).json()
    assert ready['active_members'] == ready['enrolled_members'] == ready['eligible_members'] == 0
    assert ReportGenerator().generate_daily()['total_entries'] == 0
    found = client.get('/api/dashboard/activity?q=Rahul', headers=admin).json()
    assert found['total'] == 1 and found['activities'][0]['event_source'] == 'sample'


def test_demo_retry_preserves_real_profiles_and_corrupt_vectors_are_not_enrolled(showcase):
    from app.demo_data import add_demo_data
    from app.identity import IdentityVerifier
    client, admin, _member, db = showcase
    with db.get_connection() as conn:
        conn.execute("INSERT INTO users(user_id,name,face_embedding) VALUES ('DEMO-RAHUL','Existing Person',?)", (b'not a vector',))
    assert add_demo_data('admin')['members_created'] == 5
    with db.get_connection() as conn:
        assert conn.execute("SELECT name FROM users WHERE user_id='DEMO-RAHUL'").fetchone()[0] == 'Existing Person'
        assert conn.execute("SELECT COUNT(*) FROM entry_logs WHERE recognized_id='DEMO-RAHUL'").fetchone()[0] == 0
        conn.execute("UPDATE users SET face_embedding=? WHERE user_id='DEMO-ARUN'", (np.ones(512).tobytes(),))
    users = client.get('/api/users', headers=admin).json()['users']
    assert not any(row['enrolled'] for row in users)
    assert IdentityVerifier().get_all_user_embeddings() == {}


def test_real_enrollment_promotes_demo_profile_only_after_consent(showcase, monkeypatch, tmp_path):
    import app.vision as vision
    import app.utils as utils
    import app.notification_settings as settings
    from app.demo_data import add_demo_data
    client, admin, _member, db = showcase
    add_demo_data('admin')
    settings.save_settings({'enabled': False, 'notify_on_enrollment': False})
    monkeypatch.setattr(vision, 'decode_image', lambda _: np.zeros((240,240,3), dtype=np.uint8))
    monkeypatch.setattr(vision, 'analyze_frame', lambda _: {'face_count': 1, 'quality_passed': True, 'embedding': np.ones(512)})
    monkeypatch.setattr(utils, 'save_frame', lambda *a, **k: 'images/enrolled/volunteer.jpg')
    payload = {**student_payload(), 'user_id': 'DEMO-RAHUL', 'images': ['real-photo']}
    assert client.post('/api/users/enroll', headers=admin, json=payload).status_code == 400
    assert client.post('/api/users/enroll', headers=admin, json={**payload, 'consent_given': True}).status_code == 200
    assert client.post('/api/admin/demo-data', headers=admin).json()['members_created'] == 0
    user = next(u for u in client.get('/api/users', headers=admin).json()['users'] if u['user_id'] == 'DEMO-RAHUL')
    assert user['is_demo'] == 0 and user['enrolled'] is True and user['face_enrollment_source'] == 'insightface'
