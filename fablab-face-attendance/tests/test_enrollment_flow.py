"""End-to-end API enrollment with the CV inference boundary stubbed."""

import numpy as np
from fastapi.testclient import TestClient

from app.main import app


def test_photo_enrollment_persists_member_and_is_idempotent(tmp_path, monkeypatch):
    import app.database as dbmod
    import app.utils as utils
    import app.vision as vision

    monkeypatch.setattr(dbmod, 'DATABASE_PATH', str(tmp_path / 'enrollment.db'))
    dbmod.init_db()

    frame = np.zeros((240, 240, 3), dtype=np.uint8)
    embedding = np.linspace(-1.0, 1.0, 512, dtype=np.float64)
    embedding /= np.linalg.norm(embedding)

    monkeypatch.setattr(vision, 'decode_image', lambda _payload: frame.copy())
    monkeypatch.setattr(vision, 'analyze_frame', lambda _frame: {
        'face_count': 1,
        'quality_passed': True,
        'quality_reasons': [],
        'embedding': embedding.copy(),
    })
    monkeypatch.setattr(
        utils, 'save_frame',
        lambda *_args, **_kwargs: 'images/enrolled/TEST-001.jpg')

    payload = {
        'user_id': 'TEST-001',
        'name': 'Test Member',
        'email': 'test.member@srmist.edu.in',
        'password': 'secret1',
        'payment_status': 'active',
        'consent_given': True,
        'images': ['photo-one', 'photo-two'],
    }

    with TestClient(app, raise_server_exceptions=False) as client:
        first = client.post('/api/users/enroll', json=payload)
        assert first.status_code == 200, first.text
        assert first.json()['embeddings_stored'] == 2

        payload['name'] = 'Updated Member'
        second = client.post('/api/users/enroll', json=payload)
        assert second.status_code == 200, second.text

    conn = dbmod.get_connection()
    user = conn.execute(
        'SELECT name, face_embedding, consent_given FROM users WHERE user_id=?',
        ('TEST-001',),
    ).fetchone()
    token_count = conn.execute(
        'SELECT COUNT(*) FROM tokens WHERE user_id=? AND active=1',
        ('TEST-001',),
    ).fetchone()[0]
    conn.close()

    assert user['name'] == 'Updated Member'
    assert user['face_embedding'] is not None
    assert user['consent_given'] == 1
    assert token_count == 1


def test_enrollment_explains_photo_rejection(tmp_path, monkeypatch):
    import app.database as dbmod
    import app.vision as vision

    monkeypatch.setattr(dbmod, 'DATABASE_PATH', str(tmp_path / 'rejected.db'))
    dbmod.init_db()
    monkeypatch.setattr(
        vision, 'decode_image',
        lambda _payload: np.zeros((240, 240, 3), dtype=np.uint8))
    monkeypatch.setattr(vision, 'analyze_frame', lambda _frame: {
        'face_count': 1,
        'quality_passed': False,
        'quality_reasons': ['Face too blurry: variance 42.0 < 100'],
        'embedding': None,
    })

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post('/api/users/enroll', json={
            'user_id': 'TEST-REJECT',
            'name': 'Rejected Member',
            'email': 'reject@srmist.edu.in',
            'password': 'secret1',
            'consent_given': True,
            'images': ['blurry-photo'],
        })

    assert response.status_code == 422
    assert 'photo 1' in response.json()['detail']
    assert 'too blurry' in response.json()['detail'].lower()
