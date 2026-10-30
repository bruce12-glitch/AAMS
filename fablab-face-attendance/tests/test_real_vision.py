"""Opt-in model validation using scikit-image's public NASA astronaut fixture.

Run only in disposable test environments with the full requirements installed:
    AAMS_REAL_VISION_TEST=1 python -m pytest tests/test_real_vision.py -q -s
The model cache is retained; records, evidence and notifications are isolated.
"""
import base64
import os

import pytest

from tests.test_showcase_flows import showcase, student_payload


@pytest.mark.skipif(os.getenv('AAMS_REAL_VISION_TEST') != '1', reason='Opt-in: downloads and runs real InsightFace models')
def test_actual_photo_enrollment_attendance_and_notification_queue(showcase, tmp_path, monkeypatch):
    import cv2
    from skimage.data import astronaut
    import app.utils as utils
    import app.vision as vision
    import app.notification_settings as settings
    client, admin, _member, db = showcase
    monkeypatch.setattr(utils, 'IMAGES_DIR', tmp_path / 'images')
    monkeypatch.setattr(vision, 'BASE_DIR', tmp_path)
    monkeypatch.setattr(vision, '_ENGINE', None)
    monkeypatch.setattr(vision, '_ENGINE_FAILED', False)
    monkeypatch.setattr(vision, '_ENGINE_LOADING', False)
    settings.save_settings({'enabled': False})  # Never send a real Telegram message.
    # The public fixture passed the normal size, blur, brightness and pose rules
    # in the earlier showcase verification; do not weaken those thresholds.
    frame = cv2.resize(cv2.cvtColor(astronaut(), cv2.COLOR_RGB2BGR), (700, 700))
    encoded = base64.b64encode(cv2.imencode('.jpg', frame)[1]).decode()
    result = client.post('/api/users/enroll', json={**student_payload(), 'consent_given': True, 'images': [encoded]}, headers=admin)
    assert result.status_code == 200, result.text
    assert result.json()['embeddings_stored'] >= 1
    assert vision.engine_state() == 'ready'
    payload = {'image_b64': encoded, 'continuous': True, 'skip_liveness': True}
    response = client.post('/api/entry/face-only', json=payload, headers=admin)
    assert response.status_code == 200, response.text
    assert response.json()['decision'] == 'GRANTED' and response.json()['recorded'] is True
    assert response.json()['user']['user_id'] == student_payload()['user_id']
    assert response.json()['notification']['status'] == 'queued'
    assert response.json()['notification']['telegram_sent'] is False
    assert client.post('/api/entry/face-only', json=payload, headers=admin).json()['duplicate'] is True
    with db.get_connection() as conn:
        assert conn.execute('SELECT COUNT(*) FROM entry_logs').fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM occupants WHERE status='inside'").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM alerts WHERE alert_type='ENTRY' AND sent_status='pending'").fetchone()[0] == 1
    user_id = student_payload()['user_id']
    assert client.post(f'/api/occupants/{user_id}/exit', headers=admin).status_code == 200
    assert client.post('/api/entry/face-only', json=payload, headers=admin).json()['recorded'] is True
    client.put(f'/api/users/{user_id}', json={'payment_status': 'expired'}, headers=admin)
    denied = client.post('/api/entry/face-only', json=payload, headers=admin)
    assert denied.json()['decision'] == 'DENIED' and denied.json()['tag'] == 'unpaid'
    empty = base64.b64encode(cv2.imencode('.jpg', frame * 0)[1]).decode()
    assert client.post('/api/entry/face-only', json={**payload, 'image_b64': empty}, headers=admin).json()['recorded'] is False
    print('Real InsightFace: photo enrollment, identity match, attendance, deduplication, checkout/re-entry, payment denial, empty frame and notification queue PASS (liveness explicitly bypassed for still-image fixture).')


@pytest.mark.skipif(os.getenv('AAMS_REAL_VISION_TEST') != '1', reason='Opt-in: downloads and runs real InsightFace models')
def test_two_real_identities_and_photo_variants_without_side_effects(showcase, tmp_path, monkeypatch):
    """Regression fixture, NOT a population accuracy/false-accept benchmark.

    The second public-domain US Navy portrait is distributed by Matplotlib.
    Photo transformations are not independent held-out capture sessions.
    """
    import urllib.request
    import cv2
    import numpy as np
    from skimage.data import astronaut
    import app.utils as utils
    import app.vision as vision
    import app.notification_settings as settings
    from app.liveness import LivenessChecker

    client, admin, _member, db = showcase
    monkeypatch.setattr(utils, 'IMAGES_DIR', tmp_path / 'images')
    monkeypatch.setattr(vision, 'BASE_DIR', tmp_path)
    settings.save_settings({'enabled': False, 'notify_on_enrollment': False})
    first = cv2.resize(cv2.cvtColor(astronaut(), cv2.COLOR_RGB2BGR), (700, 700))
    # A versioned official fixture, not a third-party face scraped from a profile.
    url = 'https://raw.githubusercontent.com/matplotlib/matplotlib/v3.10.7/lib/matplotlib/mpl-data/sample_data/grace_hopper.jpg'
    raw = urllib.request.urlopen(url, timeout=60).read()
    second = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_COLOR)
    assert second is not None
    def encode(frame, quality=90):
        return base64.b64encode(cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, quality])[1]).decode()
    def preview(frame, **extra):
        response = client.post('/api/entry/face-only', headers=admin, json={
            'image_b64': encode(frame), 'skip_liveness': True, 'dry_run': True, **extra})
        assert response.status_code == 200, response.text
        assert response.json()['recorded'] is False
        return response.json()
    def enroll(frame, user_id):
        response = client.post('/api/users/enroll', headers=admin, json={**student_payload(),
            'user_id': user_id, 'email': f'{user_id.lower()}@srmist.edu.in',
            'consent_given': True, 'images': [encode(frame)]})
        assert response.status_code == 200, response.text

    enroll(first, 'FIXTURE-A')
    stranger = preview(second)
    assert stranger['decision'] == 'DENIED' and stranger['diagnostics']['identity_result'] == 'UNKNOWN'
    assert stranger['similarity'] < stranger['diagnostics']['threshold']
    enroll(second, 'FIXTURE-B')
    scores = {}
    for identity, frame in [('FIXTURE-A', first), ('FIXTURE-B', second)]:
        variants = {'original': frame, 'brighter': cv2.convertScaleAbs(frame, alpha=1.05, beta=8),
                    'cropped': frame[8:-8, 8:-8],
                    'compressed': cv2.imdecode(np.frombuffer(base64.b64decode(encode(frame, 65)), np.uint8), cv2.IMREAD_COLOR)}
        for name, variant in variants.items():
            result = preview(variant)
            assert result['decision'] == 'GRANTED', result
            assert result['user']['user_id'] == identity
            scores[f'{identity}:{name}'] = result['similarity']
    face = vision.get_engine().detect_faces(first)[0]
    assert LivenessChecker().sequence_openness([face])['usable'], 'Real InsightFace eye contours must be read'
    static = preview(first, skip_liveness=False, liveness_frames_b64=[encode(first)] * 4)
    assert static['decision'] == 'DENIED' and static['tag'] == 'liveness'
    assert static['diagnostics']['liveness']['status'] == 'unknown'
    with db.get_connection() as conn:
        assert conn.execute('SELECT COUNT(*) FROM entry_logs').fetchone()[0] == 0
        assert conn.execute('SELECT COUNT(*) FROM occupants').fetchone()[0] == 0
        assert conn.execute('SELECT COUNT(*) FROM alerts').fetchone()[0] == 0
    print(f'Real two-identity regression: variant cosine scores={scores}; unenrolled portrait score={stranger["similarity"]}; threshold=0.45. Not an accuracy benchmark. Static burst denied; no attendance or Telegram writes.')
