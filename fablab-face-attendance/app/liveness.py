"""
Liveness Checker for FacePass FabLab.
Implements blink detection for anti-spoofing (§13).

Primary method: temporal eye-openness analysis over a frame sequence using
InsightFace buffalo_l landmarks:
  - `face.lmk` (106-pt, from the 2d106det model) when available
  - falls back to `face.kps` (5-pt) where only coarse openness is possible

A blink = openness drops below the closed threshold then recovers above
the open threshold within the sequence. Static photos/videos of a still
face produce no blink event -> spoof suspected.

Single-frame analysis cannot prove liveness; it returns "unknown" so the
access policy can decide (§11.2 row: liveness unknown -> deny gracefully).
"""

import logging

import cv2
import numpy as np

from app.config import get_face_config

logger = logging.getLogger(__name__)

# InsightFace 2d106det landmark layout — eye contour point groups.
LEFT_EYE_106 = list(range(33, 42))   # 33..41 inclusive
RIGHT_EYE_106 = list(range(87, 96))  # 87..95 inclusive


class LivenessChecker:
    """Blink-based liveness detection over frame sequences."""

    def __init__(self):
        config = get_face_config()
        liveness_cfg = config.get('liveness', {}) if isinstance(config, dict) else {}
        self.enabled = bool(liveness_cfg.get('enabled', True))
        self.timeout_seconds = float(liveness_cfg.get('timeout_seconds', 5))

        # Eye-openness thresholds (ratio of eye height to eye width).
        self.open_ratio_closed = float(liveness_cfg.get('open_ratio_closed', 0.14))
        self.open_ratio_open = float(liveness_cfg.get('open_ratio_open', 0.20))
        self.min_frames_between_blinks = int(liveness_cfg.get('min_frames_between_blinks', 2))

        # Head-motion challenge (§13 Method 2) — kps-based yaw proxy
        self.head_motion_enabled = bool(liveness_cfg.get('head_motion_enabled', True))
        self.head_motion_range = float(liveness_cfg.get('head_motion_range', 0.18))
        self.min_motion_frames = int(liveness_cfg.get('min_motion_frames', 4))

    # ------------------------------------------------------------------ #
    # Landmark helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _eye_points(face) -> tuple:
        """
        Extract (left_eye_pts, right_eye_pts) from an InsightFace face.

        Returns (None, None) when no usable landmarks exist.
        """
        lmk = getattr(face, 'lmk', None)
        if lmk is not None and len(lmk) >= 96:
            left = np.asarray(lmk)[LEFT_EYE_106]
            right = np.asarray(lmk)[RIGHT_EYE_106]
            return left, right

        kps = getattr(face, 'kps', None)
        if kps is not None and len(kps) >= 2:
            # 5-pt layout: [left_eye, right_eye, nose, mouth_l, mouth_r].
            # Single center points cannot express openness — return the
            # centers so callers can at least confirm eye positions exist.
            return np.asarray([kps[0]]), np.asarray([kps[1]])
        return None, None

    @staticmethod
    def eye_openness(eye_points: np.ndarray) -> float:
        """
        Eye-openness ratio = vertical spread / horizontal spread of the
        eye landmark cluster. Works for any point count (6/8/9 pts);
        ~0.25-0.45 when open, <0.12 when closed for contour points.
        For single points returns -1 (unknown).
        """
        pts = np.asarray(eye_points, dtype=np.float64)
        if len(pts) < 3:
            return -1.0
        width = float(pts[:, 0].max() - pts[:, 0].min())
        height = float(pts[:, 1].max() - pts[:, 1].min())
        if width <= 1e-6:
            return -1.0
        return height / width

    def sequence_openness(self, faces_sequence: list) -> dict:
        """
        Compute per-frame mean eye openness for a sequence of face objects.
        Returns dict with ratios list, usable flag and reason.
        """
        ratios = []
        contour_based = False
        for face in faces_sequence or []:
            left, right = self._eye_points(face)
            if left is None:
                continue
            vals = []
            if len(left) >= 3:
                vals.append(self.eye_openness(left))
                contour_based = True
            if len(right) >= 3:
                vals.append(self.eye_openness(right))
            vals = [v for v in vals if v >= 0]
            if vals:
                ratios.append(float(np.mean(vals)))
            else:
                ratios.append(-1.0)  # eyes located but openness unknowable
        usable = contour_based and any(r >= 0 for r in ratios)
        return {
            "ratios": ratios,
            "usable": usable,
            "reason": "" if usable else
            "landmark model lacks eye contours (5-pt kps only)",
        }

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def check_liveness(self, frames_sequence: list = None,
                       faces_sequence: list = None,
                       face_engine=None) -> dict:
        """
        Analyze liveness across a sequence.

        Either supply pre-detected `faces_sequence` (one face object per
        frame, may contain Nones) or raw frames + a face_engine to detect
        with. Returns:
          - status: real | spoof | unknown
          - blink_detected, openness values, frames_analyzed
        """
        base = {
            'status': 'unknown',
            'blink_detected': False,
            'openness_values': [],
            'frames_analyzed': 0,
            'reason': '',
        }

        if not self.enabled:
            base['reason'] = 'Liveness disabled by config'
            return base

        if not faces_sequence and frames_sequence and face_engine is not None:
            faces_sequence = []
            for frame in frames_sequence:
                detected = face_engine.detect_faces(frame)
                faces_sequence.append(
                    max(detected, key=lambda f: f.bbox[2] * f.bbox[3])
                    if detected else None
                )

        if not faces_sequence:
            base['reason'] = 'No faces supplied for analysis'
            return base

        seq = self.sequence_openness(faces_sequence)
        base['openness_values'] = [round(r, 4) for r in seq['ratios']]
        base['frames_analyzed'] = len(seq['ratios'])

        if not seq['usable']:
            base['reason'] = seq['reason']
            return base

        blink = self._detect_blink(seq['ratios'])
        base['blink_detected'] = blink

        positive_ratios = [r for r in seq['ratios'] if r >= 0]
        if blink:
            base['status'] = 'real'
            base['reason'] = 'Blink detected'
            return base

        # Head-motion challenge as an independent liveness signal (§13.1 M2)
        motion = self.check_head_motion(faces_sequence)
        base['head_motion'] = {'moved': motion.get('moved', False),
                               'swing': motion.get('swing')}
        if motion.get('moved'):
            base['status'] = 'real'
            base['reason'] = 'Head-motion challenge passed (no blink observed)'
            return base

        if len(positive_ratios) >= 4:
            # Enough temporal evidence and still no blink → likely a replay.
            base['status'] = 'spoof'
            base['reason'] = 'No blink or head movement across sequence'
        else:
            base['reason'] = 'Not enough frames to judge'
        return base

    def _detect_blink(self, ratios: list) -> bool:
        """Blink = observed closed dip followed by recovery within a
        plausible window. An open frame before any closure never counts."""
        was_closed_at = None
        cooldown = 0
        for i, r in enumerate(ratios):
            if r < 0:
                continue
            if cooldown > 0:
                cooldown -= 1
                continue
            if r < self.open_ratio_closed:
                if was_closed_at is None or i - was_closed_at > 15:
                    was_closed_at = i  # (re)start of a closed phase
            elif r > self.open_ratio_open and was_closed_at is not None:
                gap = i - was_closed_at
                if 1 <= gap < 15:  # recovered shortly after a real closure
                    cooldown = self.min_frames_between_blinks
                    return True
        return False

    # ------------------------------------------------------------------ #
    # Head-motion challenge (§13 Method 2)
    # ------------------------------------------------------------------ #

    @staticmethod
    def _yaw_proxy(face) -> float:
        """
        Horizontal head-turn proxy from 5-pt kps:
        (nose_x - eye_midpoint_x) / inter-eye distance.
        ~0 when facing camera, grows positive/negative on turns.
        """
        kps = getattr(face, 'kps', None)
        if kps is None or len(kps) < 3:
            return None
        left_eye, right_eye, nose = np.asarray(kps[0]), np.asarray(kps[1]), np.asarray(kps[2])
        eye_dist = float(np.linalg.norm(right_eye - left_eye))
        if eye_dist < 1e-6:
            return None
        mid = (left_eye + right_eye) / 2.0
        return float((nose[0] - mid[0]) / eye_dist)

    def check_head_motion(self, faces_sequence: list) -> dict:
        """
        Real heads drift horizontally; a held photo/screen does not.
        Returns moved flag + the per-frame proxy values.
        """
        proxies = [p for p in (self._yaw_proxy(f) for f in faces_sequence or [])
                   if p is not None]
        out = {'moved': False, 'yaw_values': [round(p, 3) for p in proxies],
               'frames_used': len(proxies)}
        if not self.head_motion_enabled or len(proxies) < self.min_motion_frames:
            out['reason'] = 'insufficient frames' if len(proxies) < self.min_motion_frames \
                else 'disabled'
            return out
        swing = max(proxies) - min(proxies)
        out['swing'] = round(swing, 3)
        out['moved'] = swing >= self.head_motion_range
        return out

    def check_liveness_single_frame(self, frame=None, face=None) -> dict:
        """Single frames can't demonstrate a blink — always 'unknown'."""
        return {
            'status': 'unknown',
            'blink_detected': False,
            'openness_values': [],
            'frames_analyzed': 1 if frame is not None else 0,
            'reason': 'Single frame — send a short frame burst for blink check',
        }
