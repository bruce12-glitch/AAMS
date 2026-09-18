"""
Continuous camera capture for unattended entry detection.

Until now nothing ever started the camera. `/api/dashboard/live` built a fresh
CameraManager and called get_status() on it without start(), so `running` was
always False and the console permanently reported "camera standby". The CV
pipeline worked — it just had no frames coming in.

This service owns the camera for the lifetime of the process:

  CameraManager (background thread, configured fps/resolution)
        -> every `interval_seconds`, grab a frame
        -> analyze_frame: detect -> quality -> embed
        -> IdentityVerifier.verify_face_only
        -> on a confident match, record the entry (subject to a per-person
           cooldown so one person standing at the door does not generate a
           row per second)

Design notes:
  - Runs in its own daemon thread; never blocks the API.
  - Failures are logged and swallowed — a camera that is unplugged must not
    take the API down.
  - Disabled by default via `capture.enabled` in config.yaml. Turn it on only
    where a real camera is attached (the lab host, not a laptop by reflex).
"""

import logging
import threading
import time
from datetime import datetime

logger = logging.getLogger(__name__)


def _now_iso():
    """ISO-8601 timestamp.

    SQLite's CURRENT_TIMESTAMP renders as 'YYYY-MM-DD HH:MM:SS' while the rest
    of the codebase writes ISO with a 'T'. Mixing the two in one row (this
    service writes last_seen_time, _finalize writes entry_time) breaks
    duration maths in the occupancy view. Use ISO consistently here.
    """
    return datetime.now().isoformat()


class CaptureService:
    """Owns the camera and turns recognised faces into entry records."""

    def __init__(self, interval_seconds=2.0, cooldown_seconds=45.0):
        self.interval = interval_seconds
        self.cooldown = cooldown_seconds
        self.running = False
        self.thread = None
        self.camera = None

        # Last decision, surfaced by GET /api/dashboard/live.
        self.last_event = None
        self.last_seen = {}          # user_id -> monotonic timestamp
        self.frames_processed = 0

    # ------------------------------------------------------------------ #
    # lifecycle
    # ------------------------------------------------------------------ #
    def start(self):
        if self.running:
            return
        from app.camera import CameraManager

        self.camera = CameraManager()
        try:
            self.camera.start()
        except Exception as exc:
            # No camera, or it is busy. Not fatal — the API must still serve.
            logger.warning('Capture service not started: %s', exc)
            self.camera = None
            return

        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True,
                                       name='capture-service')
        self.thread.start()
        logger.info('Capture service started (every %.1fs, cooldown %.0fs)',
                    self.interval, self.cooldown)

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=3.0)
        if self.camera:
            try:
                self.camera.stop()
            except Exception:
                pass
        logger.info('Capture service stopped')

    # ------------------------------------------------------------------ #
    # main loop
    # ------------------------------------------------------------------ #
    def _loop(self):
        # Let auto-exposure settle; early frames are often too dark to pass
        # the quality gate, and we would log nothing but rejections.
        time.sleep(2.0)

        while self.running:
            try:
                self._tick()
            except Exception as exc:
                # Never let a per-frame error kill the loop.
                logger.error('Capture tick failed: %s', exc)
            time.sleep(self.interval)

    def _tick(self):
        if not self.camera or not self.camera.is_online():
            return

        frame = self.camera.capture_frame()
        if frame is None:
            return

        from app.vision import analyze_frame

        analysis = analyze_frame(frame)
        self.frames_processed += 1

        if analysis.get('face_count', 0) == 0:
            return
        if not analysis.get('quality_passed'):
            return

        embedding = analysis.get('embedding')
        if embedding is None:
            return

        from app.identity import IdentityVerifier

        result = IdentityVerifier().verify_face_only(embedding)
        if result.get('result') != 'MATCH':
            self.last_event = {
                'recognized_id': result.get('detected_user'),
                'similarity': round(result.get('similarity', 0.0), 3),
                'decision': 'UNKNOWN',
                'at': time.time(),
            }
            return

        user = result.get('user') or {}
        user_id = user.get('user_id') or result.get('detected_user')
        if not user_id:
            return

        # Per-person cooldown: one entry per person per cooldown window.
        now = time.monotonic()
        if now - self.last_seen.get(user_id, -1e9) < self.cooldown:
            return
        self.last_seen[user_id] = now

        self._record_entry(user, result, frame)

    # ------------------------------------------------------------------ #
    # persistence
    # ------------------------------------------------------------------ #
    def _record_entry(self, user, result, frame):
        from app.config import get_config
        from app.utils import save_frame

        payment = user.get('payment_status', 'inactive')
        granted = payment == 'active'
        decision = 'GRANTED' if granted else 'DENIED'
        tag = 'authorized' if granted else 'unpaid'
        similarity = round(result.get('similarity', 0.0), 4)
        now_iso = _now_iso()

        try:
            evidence = save_frame(frame, 'logs', prefix=user.get('user_id'))
        except Exception:
            evidence = None

        location = get_config().get('system', {}).get('location', 'fab_lab_entrance')

        from app.database import get_connection

        conn = get_connection()
        cur = conn.cursor()
        try:
            cur.execute('''
                INSERT INTO entry_logs (event_time, claimed_id, recognized_id,
                    similarity, payment_status, liveness_status, decision,
                    reason, tag, image_path, location)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                now_iso,
                user.get('user_id'), user.get('user_id'), similarity,
                payment, 'unknown',
                decision,
                'Automatic entry (camera)' if granted else f'Payment {payment}',
                tag, evidence, location,
            ))

            if granted:
                # Only track occupancy for people allowed in.
                cur.execute('''
                    SELECT id FROM occupants
                    WHERE user_id = ? AND status = 'inside'
                ''', (user.get('user_id'),))
                if cur.fetchone() is None:
                    cur.execute('''
                        INSERT INTO occupants (user_id, entry_time,
                            last_seen_time, status)
                        VALUES (?, ?, ?, 'inside')
                    ''', (user.get('user_id'), now_iso, now_iso))
                else:
                    cur.execute('''
                        UPDATE occupants SET last_seen_time = ?
                        WHERE user_id = ? AND status = 'inside'
                    ''', (now_iso, user.get('user_id')))

            conn.commit()
        finally:
            conn.close()

        self.last_event = {
            'recognized_id': user.get('user_id'),
            'name': user.get('name'),
            'similarity': similarity,
            'decision': decision,
            'tag': tag,
            'at': time.time(),
        }
        logger.info('Auto entry: %s -> %s (%.2f)', user.get('user_id'),
                    decision, similarity)

    # ------------------------------------------------------------------ #
    # status
    # ------------------------------------------------------------------ #
    def get_status(self):
        online = bool(self.camera and self.camera.is_online())
        cam_status = self.camera.get_status() if self.camera else {}
        return {
            'online': online,
            'source': cam_status.get('source'),
            'fps': cam_status.get('fps'),
            'resolution': cam_status.get('resolution'),
            'frames_processed': self.frames_processed,
            'last_event': self.last_event,
        }


# Process-wide singleton. The API and the capture loop must agree on one
# camera handle; opening VideoCapture twice on the same index fails on most
# Windows drivers.
_SERVICE = None
_LOCK = threading.Lock()


def get_capture_service():
    global _SERVICE
    with _LOCK:
        if _SERVICE is None:
            from app.config import get_config
            cfg = get_config().get('capture', {})
            _SERVICE = CaptureService(
                interval_seconds=float(cfg.get('interval_seconds', 2.0)),
                cooldown_seconds=float(cfg.get('cooldown_seconds', 45.0)),
            )
        return _SERVICE
