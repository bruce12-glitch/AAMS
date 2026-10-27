"""No-write photo checks and truthful recognition diagnostics."""
import numpy as np
import pytest

from tests.test_showcase_flows import showcase, student_payload


@pytest.fixture
def photo_pipeline(showcase, monkeypatch):
    import app.vision as vision
    import app.notification_settings as settings
    client, admin, member, db = showcase
    settings.save_settings({'enabled': False, 'notify_on_enrollment': False})
    vector = np.zeros(512)
    vector[0] = 1
    analysis = {'face_count': 1, 'quality_passed': True, 'quality_reasons': [],
                'embedding': vector, 'bbox': [10, 10, 180, 200],
                'quality_metrics': {'face_width_px': 170, 'blur_variance': 140.0}}
    monkeypatch.setattr(vision, 'decode_image', lambda _: np.zeros((240, 320, 3), dtype=np.uint8))
    monkeypatch.setattr(vision, 'analyze_frame', lambda _: analysis)
    monkeypatch.setattr(vision, 'save_evidence', lambda *_: pytest.fail('Preview saved evidence'))
    return client, admin, member, db, vector, analysis


def check(client, admin, **values):
    path = '/api/entry/process' if 'token_value' in values else '/api/entry/face-only'
    response = client.post(path, headers=admin, json={'image_b64': 'test-photo', 'dry_run': True, 'skip_liveness': True, **values})
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload['recorded'] is False and payload['dry_run'] is True
    assert payload['notification']['status'] == 'not_requested'
    return payload


def test_setup_errors_are_not_fake_zero_similarity_matches(photo_pipeline):
    client, admin, _member, db, _vector, _ = photo_pipeline
    empty = check(client, admin)
    assert empty['diagnostics']['identity_result'] == 'EMPTY_GALLERY'
    assert empty['diagnostics']['comparison_performed'] is False
    invalid = check(client, admin, token_value='11')
    assert invalid['diagnostics']['identity_result'] == 'INVALID_TOKEN'
    assert 'pass not valid' in invalid['reason']
    assert client.post('/api/users', headers=admin, json=student_payload()).status_code == 200
    assert client.post('/api/users/STUDENT-001/tokens/revoke', headers=admin).status_code == 200
    not_enrolled = check(client, admin, token_value='STUDENT-001')
    assert not_enrolled['diagnostics']['identity_result'] == 'NO_EMBEDDINGS'
    assert 'Enroll face' in not_enrolled['reason']
    with db.get_connection() as conn:
        assert conn.execute('SELECT COUNT(*) FROM entry_logs').fetchone()[0] == 0
        assert conn.execute('SELECT COUNT(*) FROM alerts').fetchone()[0] == 0


def test_positive_and_negative_comparisons_do_not_mark_attendance(photo_pipeline):
    client, admin, _member, db, vector, analysis = photo_pipeline
    client.post('/api/users', headers=admin, json=student_payload())
    with db.get_connection() as conn:
        conn.execute('UPDATE users SET face_embedding=? WHERE user_id=?', (vector.tobytes(), 'STUDENT-001'))
    result = check(client, admin)
    assert result['decision'] == 'GRANTED'
    assert result['diagnostics']['comparison_performed'] is True
    assert result['diagnostics']['threshold'] == 0.45
    assert result['diagnostics']['enrolled_users'] == 1
    assert result['diagnostics']['bbox'] == [10, 10, 180, 200]
    assert result['diagnostics']['image_size'] == {'width': 320, 'height': 240}
    assert result['diagnostics']['liveness']['status'] == 'skipped'
    analysis['embedding'] = np.roll(vector, 1)
    assert check(client, admin)['diagnostics']['identity_result'] == 'UNKNOWN'
    with db.get_connection() as conn:
        assert conn.execute('SELECT COUNT(*) FROM entry_logs').fetchone()[0] == 0
        assert conn.execute('SELECT COUNT(*) FROM occupants').fetchone()[0] == 0
        assert conn.execute('SELECT COUNT(*) FROM alerts').fetchone()[0] == 0


@pytest.mark.parametrize('face_count', [0, 1])
def test_no_face_and_low_quality_preview_have_no_side_effects(photo_pipeline, face_count):
    client, admin, _member, db, _, analysis = photo_pipeline
    analysis.update(face_count=face_count, quality_passed=False, quality_reasons=['Face too blurry'])
    result = check(client, admin)
    assert result['decision'] == 'DENIED'
    assert result['diagnostics']['comparison_performed'] is False
    with db.get_connection() as conn:
        assert conn.execute('SELECT COUNT(*) FROM entry_logs').fetchone()[0] == 0
        assert conn.execute('SELECT COUNT(*) FROM alerts').fetchone()[0] == 0


def test_preview_still_requires_authentication_in_production(photo_pipeline, monkeypatch):
    client, _admin, _member, _db, _, _ = photo_pipeline
    monkeypatch.setenv('AAMS_ENV', 'production')
    assert client.post('/api/entry/face-only', json={'image_b64': 'x', 'dry_run': True}).status_code == 401


def test_embedding_storage_handles_legacy_float32_and_corruption():
    from app.identity import _decode_embedding
    vector = np.linspace(-1, 1, 512)
    assert np.allclose(_decode_embedding(vector.astype(np.float32).tobytes()), vector / np.linalg.norm(vector))
    for blob in (b'bad', np.zeros(512).tobytes(), np.full(512, np.nan).tobytes()):
        assert _decode_embedding(blob) is None


def test_cropped_face_cannot_skip_quality_checks():
    from app.face_engine import FaceEngine
    from types import SimpleNamespace
    engine = object.__new__(FaceEngine)
    engine.min_face_size, engine.blur_threshold = 120, 100
    engine.brightness_min, engine.brightness_max = 40, 220
    face = SimpleNamespace(bbox=np.array([-150, -150, -1, -1]), pose=None)
    passed, reasons = engine.quality_check(face, np.zeros((240, 240, 3), dtype=np.uint8))
    assert not passed and any('cut off' in reason for reason in reasons)


def test_enrollment_rejects_mixed_people_before_writing(photo_pipeline, monkeypatch):
    client, admin, _member, db, vector, _ = photo_pipeline
    import app.vision as vision
    calls = []
    original = vision.analyze_frame
    def analyze(frame):
        result = {**original(frame), 'embedding': vector if not calls else np.roll(vector, 1)}
        calls.append(1)
        return result
    monkeypatch.setattr(vision, 'analyze_frame', analyze)
    response = client.post('/api/users/enroll', headers=admin, json={**student_payload(), 'consent_given': True, 'images': ['one', 'other-person']})
    assert response.status_code == 422 and 'same person' in response.text
    with db.get_connection() as conn:
        assert conn.execute('SELECT COUNT(*) FROM users').fetchone()[0] == 0
