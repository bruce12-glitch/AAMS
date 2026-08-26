"""
Tests for the blink-based LivenessChecker (ยง13).

Uses lightweight fake face objects carrying either 106-pt contour
landmarks or 5-pt kps, so no ONNX models are required.
"""

import numpy as np
import pytest

from app.liveness import LivenessChecker


def make_face_106(left_open=0.32, right_open=None):
    """Fake InsightFace face with 106-pt landmarks (eye contours present)."""
    if right_open is None:
        right_open = left_open
    lmk = np.zeros((106, 2))

    def fill(indices, openness):
        xs = np.linspace(0, 10, len(indices))
        ys = np.linspace(0, 10 * openness, len(indices))
        lmk[indices, 0] = xs
        lmk[indices, 1] = ys

    fill(range(33, 42), left_open)
    fill(range(87, 96), right_open)

    class Face:
        pass

    f = Face()
    f.lmk = lmk
    return f


def make_face_kps_only():
    class Face:
        pass

    f = Face()
    f.kps = np.array([[10, 10], [30, 10], [20, 25], [12, 35], [28, 35]], dtype=float)
    return f


@pytest.fixture
def checker():
    return LivenessChecker()


def test_eye_openness_ratio(checker):
    pts = np.array([[0, 0], [5, 1], [10, 0], [5, 3]], dtype=float)
    ratio = checker.eye_openness(pts)
    assert 0 < ratio < 1


def test_single_point_openness_unknown(checker):
    assert checker.eye_openness(np.array([[5, 5]])) == -1.0


def test_blink_detected_on_dip_and_recovery(checker):
    open_face = make_face_106(0.34)
    closed_face = make_face_106(0.08)
    seq = [open_face] * 4 + [closed_face] * 3 + [open_face] * 4

    result = checker.check_liveness(faces_sequence=seq)

    assert result['status'] == 'real'
    assert result['blink_detected'] is True
    assert result['frames_analyzed'] == len(seq)


def test_no_blink_over_long_sequence_is_spoof(checker):
    seq = [make_face_106(0.34)] * 8  # eyes wide open the whole time

    result = checker.check_liveness(faces_sequence=seq)

    assert result['status'] == 'spoof'
    assert result['blink_detected'] is False


def test_short_sequence_stays_unknown(checker):
    seq = [make_face_106(0.34)] * 2  # not enough temporal evidence

    result = checker.check_liveness(faces_sequence=seq)

    assert result['status'] == 'unknown'


def test_kps_only_faces_are_not_judged(checker):
    seq = [make_face_kps_only()] * 6

    result = checker.check_liveness(faces_sequence=seq)

    assert result['status'] == 'unknown'
    assert 'landmark' in result['reason']


def test_disabled_checker_returns_unknown(checker):
    checker.enabled = False

    result = checker.check_liveness(faces_sequence=[make_face_106()])

    assert result['status'] == 'unknown'
    assert 'disabled' in result['reason'].lower()


def test_single_frame_api_never_claims_real(checker):
    result = checker.check_liveness_single_frame(face=make_face_106())

    assert result['status'] == 'unknown'


# ---------------------------------------------------------------- #
# Head-motion challenge (ง13 Method 2)
# ---------------------------------------------------------------- #

def make_face_with_kps(nose_offset):
    class Face:
        pass

    f = Face()
    kps = np.array([
        [10.0, 10.0], [30.0, 10.0], [20.0 + nose_offset, 25.0],
        [12.0, 35.0], [28.0, 35.0]
    ])
    f.kps = kps
    return f


def test_head_motion_detected_on_swing(checker):
    seq = [make_face_with_kps(o) for o in (-4, -2, 0, 2, 4)]
    result = checker.check_head_motion(seq)
    assert result['moved'] is True
    assert result['swing'] >= checker.head_motion_range


def test_static_sequence_does_not_pass_motion(checker):
    seq = [make_face_with_kps(0.3)] * 8   # a held photo never moves
    result = checker.check_head_motion(seq)
    assert result['moved'] is False


def test_motion_rescues_no_blink_sequence(checker):
    # Eyes open the whole time (no blink) but head clearly turns.
    open_face = make_face_106(0.34)
    closed_pose_offsets = (-4, -2, 0, 2, 4)
    # give each face both lmk (open eyes) and a moving kps
    for f, off in zip([open_face] * 5, closed_pose_offsets):
        f.kps = make_face_with_kps(off).kps
    result = checker.check_liveness(faces_sequence=[open_face] * 5 if False else [
        _merged(open_face, off) for off in closed_pose_offsets
    ])
    assert result['status'] == 'real'
    assert 'motion' in result['reason'].lower()


def _merged(base_face, nose_offset):
    import copy
    f = copy.copy(base_face)
    f.kps = make_face_with_kps(nose_offset).kps
    return f
