"""Similar enrolled identities must never be resolved by row order."""
import numpy as np
import pytest

from tests.test_showcase_flows import showcase, student_payload


@pytest.mark.parametrize('token_mode', [False, True])
def test_duplicate_identity_is_denied_without_security_alert(showcase, monkeypatch, token_mode):
    import app.vision as vision
    import app.notification_settings as settings
    client, admin, _member, db = showcase
    settings.save_settings({'enabled': False, 'notify_on_enrollment': False})
    for user_id in ('FIRST', 'SECOND'):
        assert client.post('/api/users', headers=admin, json={**student_payload(), 'user_id': user_id, 'email': f'{user_id}@srmist.edu.in'}).status_code == 200
    assert client.post('/api/users/FIRST/tokens/revoke', headers=admin).status_code == 200
    vector = np.zeros(512)
    vector[0] = 1
    with db.get_connection() as conn:
        conn.execute('UPDATE users SET face_embedding=?', (vector.tobytes(),))
    monkeypatch.setattr(vision, 'decode_image', lambda _: np.zeros((240,240,3), np.uint8))
    monkeypatch.setattr(vision, 'analyze_frame', lambda _: {
        'face_count': 1, 'quality_passed': True, 'quality_reasons': [], 'embedding': vector})
    payload = {'image_b64': 'photo', 'skip_liveness': True, 'dry_run': True}
    if token_mode:
        payload['token_value'] = 'FIRST'
    result = client.post('/api/entry/process' if token_mode else '/api/entry/face-only', headers=admin, json=payload).json()
    assert result['decision'] == 'DENIED' and result['tag'] == 'ambiguous'
    assert result['diagnostics']['identity_result'] == 'AMBIGUOUS'
    assert result['diagnostics']['comparison_performed'] is True
    assert result['diagnostics']['match_margin'] == 0
    assert result['diagnostics']['min_match_margin'] == 0.05
    assert result['user'] is None or result['user']['user_id'] == 'FIRST'
    with db.get_connection() as conn:
        assert conn.execute('SELECT COUNT(*) FROM occupants').fetchone()[0] == 0
        assert conn.execute('SELECT COUNT(*) FROM alerts').fetchone()[0] == 0


def test_margin_uses_different_people_not_same_members_multiple_photos():
    from app.identity import IdentityVerifier
    verifier = IdentityVerifier()
    vector = np.array([1.,0.])
    assert verifier._ambiguous_match(vector, {'one': [vector, vector, vector]}, 1) is None
    assert verifier._ambiguous_match(vector, {'one': [vector], 'two': [np.array([0.,1.])]}, 1) is None
    assert verifier._ambiguous_match(vector, {'one': [vector], 'two': [np.array([.99,.01])]}, 1)['result'] == 'AMBIGUOUS'
    # A close tie below threshold is simply UNKNOWN, not a confident tie.
    assert verifier._ambiguous_match(vector, {'one': [np.array([0.,1.])], 'two': [np.array([0.,-1.])]}, 0) is None


def test_claimed_face_above_threshold_cannot_override_stronger_other_person(showcase):
    from app.identity import IdentityVerifier
    client, admin, _member, db = showcase
    import app.notification_settings as settings
    settings.save_settings({'enabled': False, 'notify_on_enrollment': False})
    vector = np.zeros(512)
    vector[0] = 1
    other = np.zeros(512)
    other[:2] = [.6,.8]
    for user_id, reference in [('CLAIMED', other), ('ACTUAL', vector)]:
        assert client.post('/api/users', headers=admin, json={**student_payload(), 'user_id': user_id, 'email': f'{user_id}@srmist.edu.in'}).status_code == 200
        with db.get_connection() as conn:
            conn.execute('UPDATE users SET face_embedding=? WHERE user_id=?', (reference.tobytes(), user_id))
    client.post('/api/users/CLAIMED/tokens/revoke', headers=admin)
    result = IdentityVerifier().verify_token_face('CLAIMED', vector)
    assert result['similarity'] > .45
    assert result['result'] == 'PROXY' and result['detected_user'] == 'ACTUAL'
