"""Fixed-scale focus measurements and bounded burst recovery, not fake matches."""
from types import SimpleNamespace

import cv2
import numpy as np
import pytest

from tests.test_showcase_flows import showcase, student_payload


def test_focus_gate_does_not_reject_same_detail_when_face_is_larger():
    from app.face_engine import FaceEngine
    engine = object.__new__(FaceEngine)
    engine.min_face_size, engine.blur_threshold = 120, 100
    engine.brightness_min, engine.brightness_max = 40, 220
    texture = np.random.default_rng(42).integers(60, 190, (140,140,3), dtype=np.uint8)
    scores, raw_scores = [], []
    for size in (140, 309, 600):
        frame = cv2.resize(texture, (size,size))
        face = SimpleNamespace(bbox=np.array([0,0,size,size]), pose=None)
        passed, reasons, metrics = engine.quality_check(face, frame, with_metrics=True)
        assert passed, reasons
        assert metrics['blur_reference_px'] == 112
        scores.append(metrics['blur_variance'])
        raw_scores.append(metrics['blur_variance_raw'])
    assert raw_scores[-1] < 100, 'The enlarged capture reproduces the old false rejection'
    assert min(scores) / max(scores) > min(raw_scores) / max(raw_scores)
    blurred = cv2.GaussianBlur(cv2.resize(texture,(309,309)), (0,0), 12)
    face = SimpleNamespace(bbox=np.array([0,0,309,309]), pose=None)
    passed, reasons = engine.quality_check(face, blurred)
    assert not passed and any('blurry' in reason for reason in reasons)
    for frame in (np.full((309,309,3), 15, dtype=np.uint8), np.full((309,309,3), 240, dtype=np.uint8)):
        assert not engine.quality_check(face, frame)[0]


@pytest.mark.parametrize('live_status', ['real', 'unknown'])
def test_quality_recovery_still_requires_liveness(showcase, monkeypatch, live_status):
    import app.vision as vision
    import app.notification_settings as settings
    from app.liveness import LivenessChecker
    client, admin, _member, db = showcase
    settings.save_settings({'enabled': False, 'notify_on_enrollment': False})
    client.post('/api/users', headers=admin, json=student_payload())
    vector = np.ones(512)
    with db.get_connection() as conn:
        conn.execute('UPDATE users SET face_embedding=?', (vector.tobytes(),))
    monkeypatch.setattr(vision, 'decode_image', lambda value: np.full((240,240,3), int(value), dtype=np.uint8))
    def analyze(frame):
        passing = frame[0,0,0] == 1
        return {'face_count': 1, 'quality_passed': passing, 'quality_reasons': [] if passing else ['Face too blurry'], 'embedding': vector}
    monkeypatch.setattr(vision, 'analyze_frame', analyze)
    monkeypatch.setattr(vision, 'get_engine', lambda: object())
    def liveness(self, **kwargs):
        assert len(kwargs['frames_sequence']) == 5 and np.array_equal(kwargs['reference_embedding'], vector)
        return {'status': live_status, 'blink_detected': live_status == 'real', 'frames_analyzed': 5, 'reason': 'controlled blink result'}
    monkeypatch.setattr(LivenessChecker, 'check_liveness', liveness)
    response = client.post('/api/entry/face-only', headers=admin, json={
        'image_b64': '2', 'liveness_frames_b64': ['1','1','1','1','2'], 'dry_run': True})
    assert response.status_code == 200, response.text
    result = response.json()
    assert result['decision'] == ('GRANTED' if live_status == 'real' else 'DENIED')
    assert result['diagnostics']['frame_selection']['quality_frame_found'] is True
    assert result['diagnostics']['quality']['passed'] is True
    assert result['recorded'] is False
    with db.get_connection() as conn:
        assert conn.execute('SELECT COUNT(*) FROM entry_logs').fetchone()[0] == 0


def test_burst_recovery_is_bounded_and_does_not_accept_all_bad_frames(showcase, monkeypatch):
    import app.vision as vision
    client, admin, _member, _db = showcase
    calls = []
    monkeypatch.setattr(vision, 'decode_image', lambda value: np.full((240,240,3), int(value), dtype=np.uint8))
    def analyze(frame):
        calls.append(1)
        return {'face_count': 1, 'quality_passed': False, 'quality_reasons': ['Face too blurry'], 'embedding': np.ones(512)}
    monkeypatch.setattr(vision, 'analyze_frame', analyze)
    response = client.post('/api/entry/face-only', headers=admin, json={'image_b64': '12', 'liveness_frames_b64': [str(i) for i in range(12)], 'dry_run': True})
    assert response.status_code == 200 and response.json()['tag'] == 'quality'
    assert len(calls) == 13 and not response.json()['diagnostics']['comparison_performed']
    assert client.post('/api/entry/face-only', headers=admin, json={'image_b64': '12', 'liveness_frames_b64': ['1'] * 13, 'dry_run': True}).status_code == 422


def test_burst_selects_best_passing_frame_anywhere_not_first_pass(monkeypatch):
    import app.vision as vision
    frames = [np.full((5,5,3), i, np.uint8) for i in range(10)]
    calls = []
    def analyze(frame):
        index = int(frame[0,0,0])
        calls.append(index)
        return {'face_count': 1, 'quality_passed': index < 4, 'quality_metrics': {'blur_variance': 900 - index * 100}}
    monkeypatch.setattr(vision, 'analyze_frame', analyze)
    selected, analysis, results, info = vision.select_burst_frame(frames[-1], frames)
    assert selected is frames[0] and analysis['quality_passed']
    assert len(results) == 10 and info['selected_burst_index'] == 0
    assert len(calls) == 10, 'Last frame must not be inferred twice'


@pytest.mark.parametrize('multi_index', [None, 1])
def test_cached_burst_keeps_multi_face_and_same_person_checks(showcase, monkeypatch, multi_index):
    import app.vision as vision
    import app.notification_settings as settings
    from app.liveness import LivenessChecker
    client, admin, _member, db = showcase
    settings.save_settings({'enabled': False, 'notify_on_enrollment': False})
    client.post('/api/users', headers=admin, json=student_payload())
    vector = np.ones(512)
    with db.get_connection() as conn:
        conn.execute('UPDATE users SET face_embedding=?', (vector.tobytes(),))
    frames = [np.full((240,240,3), i, dtype=np.uint8) for i in range(5)]
    faces = [object() for _ in frames]
    monkeypatch.setattr(vision, 'decode_image', lambda value: frames[int(value)])
    monkeypatch.setattr(vision, 'get_engine', lambda: object())
    def analyze(frame):
        index = int(frame[0,0,0])
        return {'face_count': 2 if index == multi_index else 1, 'quality_passed': True,
                'quality_reasons': [], 'embedding': vector, '_face_obj': faces[index],
                'quality_metrics': {'blur_variance': 500 - index}}
    monkeypatch.setattr(vision, 'analyze_frame', analyze)
    def liveness(self, **kwargs):
        assert multi_index is None, 'Multi-face burst must not be collapsed to one cached face'
        assert kwargs['frames_sequence'] is None and kwargs['faces_sequence'] == faces
        assert np.array_equal(kwargs['reference_embedding'], vector)
        return {'status': 'unknown', 'blink_detected': False, 'frames_analyzed': 5, 'reason': 'Face changed during blink capture'}
    monkeypatch.setattr(LivenessChecker, 'check_liveness', liveness)
    result = client.post('/api/entry/face-only', headers=admin, json={
        'image_b64': '4', 'liveness_frames_b64': [str(i) for i in range(5)], 'dry_run': True}).json()
    assert result['decision'] == 'DENIED' and result['tag'] == 'liveness'
    assert 'Multiple faces' in result['reason'] or result['diagnostics']['liveness']['status'] == 'unknown'
    assert not result['recorded']
