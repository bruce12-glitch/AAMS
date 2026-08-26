"""
Entry Processing API Routes for FacePass FabLab.
Implements POST /api/entry/process, /api/entry/face-only, /api/entry/simulate.

Preferred mode (Â§9 pipeline, server-side CV):
  client sends base64 image(s); server decodes â†’ detects faces â†’
  quality-checks â†’ extracts embedding â†’ (optional) blink liveness over
  a frame burst â†’ matches identity â†’ evaluates policy â†’ logs + alerts.

Legacy compatibility: clients may still send a raw `face_embedding`
array (useful for tests); it bypasses detection but everything
downstream is identical.
"""

import logging
import time
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix='/api/entry', tags=['entry'])


class EntryRequest(BaseModel):
    token_value: Optional[str] = None
    face_embedding: Optional[List[float]] = None   # legacy path
    image_b64: Optional[str] = None                # preferred path
    liveness_frames_b64: Optional[List[str]] = None  # short burst for blink check
    skip_liveness: bool = False                    # single-snapshot testing


class SimulateRequest(BaseModel):
    scenario: str  # authorized/proxy/unpaid/unknown/spoof/tailgate


# ------------------------------------------------------------------ #
# Shared server-side pipeline
# ------------------------------------------------------------------ #

async def _run_pipeline(request: EntryRequest, mode: str) -> dict:
    """
    Full decision flow shared by /process and /face-only.
    Returns the API response dict; persists log/alert/occupancy.
    """
    t0 = time.perf_counter()
    import numpy as np

    from app.access_policy import AccessDecision
    from app.alerts import AlertService
    from app.identity import IdentityVerifier
    from app.liveness import LivenessChecker
    from app.occupancy import OccupancyTracker
    from app.utils import get_current_time_iso
    from app.vision import (
        VisionUnavailableError,
        analyze_frame,
        decode_image,
        frames_from_payloads,
        get_engine,
        save_evidence,
    )

    # ---- 1. Obtain embedding ---------------------------------------- #
    frame = None
    evidence_rel = None
    face_count = 0
    quality_note = None

    if request.image_b64:
        try:
            frame = decode_image(request.image_b64)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

        try:
            analysis = analyze_frame(frame)
        except VisionUnavailableError as exc:
            raise HTTPException(status_code=503, detail=f'CV engine unavailable: {exc}')

        face_count = analysis['face_count']
        evidence_rel = save_evidence(frame, 'logs')

        if face_count == 0:
            return await _finalize(
                latency_ms=round((time.perf_counter() - t0) * 1000, 1),
                decision='DENIED', reason='No face detected in image',
                tag='noface', alert_type='NOFACE', user=None,
                similarity=0.0, liveness_status='unknown',
                claimed=request.token_value, evidence=evidence_rel,
                extra={'face_count': 0},
            )
        if not analysis['quality_passed']:
            return await _finalize(
                latency_ms=round((time.perf_counter() - t0) * 1000, 1),
                decision='DENIED',
                reason=f"Low quality face: {'; '.join(analysis['quality_reasons'])}",
                tag='noface', alert_type=None, user=None,
                similarity=0.0, liveness_status='unknown',
                claimed=request.token_value, evidence=evidence_rel,
                extra={'face_count': face_count, 'quality': analysis['quality_reasons']},
            )

        embedding = analysis['embedding']
    elif request.face_embedding is not None:
        embedding = np.asarray(request.face_embedding, dtype=np.float64)
        if embedding.size == 0:
            raise HTTPException(status_code=400, detail='Empty embedding')
    else:
        raise HTTPException(
            status_code=400,
            detail='Provide image_b64 (preferred) or face_embedding'
        )

    # ---- 2. Liveness ------------------------------------------------- #
    liveness_status = 'unknown'
    if not request.skip_liveness and frame is not None:
        frames, bad = frames_from_payloads(request.liveness_frames_b64 or [])
        if bad:
            logger.warning('%d liveness frames failed to decode', bad)
        if len(frames) >= 2:
            engine = get_engine()
            checker = LivenessChecker()
            live = checker.check_liveness(frames_sequence=frames,
                                          face_engine=engine)
            liveness_status = live['status']
        else:
            liveness_status = 'unknown'
            quality_note = 'send >=2 frames for blink liveness'

    # ---- 3. Identity ------------------------------------------------- #
    # Normalize the claimed token: accept either the raw user_id or a full
    # signed QR payload (Â§27.3) â€” the latter is verified server-side here.
    token_value = request.token_value
    if mode == 'token_face':
        if not token_value:
            raise HTTPException(status_code=400, detail='Token value required')
        if token_value.strip().startswith('{'):
            from app.qr_manager import QRManager
            verdict = QRManager().verify_token(token_value)
            if not verdict.get('valid'):
                return await _finalize(
                latency_ms=round((time.perf_counter() - t0) * 1000, 1),
                    decision='DENIED',
                    reason=f"Invalid token: {verdict.get('reason', 'rejected')}",
                    tag='unknown', alert_type='UNKNOWN', user=None,
                    similarity=0.0, liveness_status=liveness_status,
                    claimed=None, evidence=evidence_rel,
                    extra={'face_count': face_count},
                )
            token_value = verdict['user_id']

    verifier = IdentityVerifier()
    if mode == 'token_face':
        result = verifier.verify_token_face(token_value, embedding)
        payment_user = result.get('claimed_user') or {}
    else:
        result = verifier.verify_face_only(embedding)
        payment_user = result.get('user') or {}

    detected_user = result.get('detected_user') or (
        result.get('user') or {}).get('user_id')

    # Face-only UNKNOWN needs no token context to be flagged.
    if mode == 'face_only':
        face_count = max(face_count, 1)

    # ---- 4. Policy --------------------------------------------------- #
    payment_status = payment_user.get('payment_status', 'inactive')
    policy = AccessDecision()
    decision = policy.evaluate_access(
        claimed_id=token_value,
        face_result=result,
        payment_status=payment_status,
        liveness_status=liveness_status,
        face_count=face_count if request.image_b64 else 1,
    )

    user_info = result.get('claimed_user') or result.get('user')
    return await _finalize(
                latency_ms=round((time.perf_counter() - t0) * 1000, 1),
        decision=decision['decision'],
        reason=decision['reason'] + (f' ({quality_note})' if quality_note else ''),
        tag=decision['tag'],
        alert_type=decision.get('alert_type'),
        user=user_info,
        similarity=result.get('similarity', 0.0),
        liveness_status=liveness_status,
        claimed=token_value or detected_user,
        evidence=evidence_rel,
        extra={
            'face_count': face_count,
            'recognized_id': detected_user,
        },
    )


async def _finalize(decision, reason, tag, alert_type, user, similarity,
                    liveness_status, claimed, evidence, extra,
                    latency_ms=None) -> dict:
    """Persist log + occupancy + alert, then build the response."""
    from app.alerts import AlertService
    from app.database import get_connection
    from app.occupancy import OccupancyTracker

    recognized = (extra or {}).get('recognized_id')

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO entry_logs (claimed_id, recognized_id, similarity,
                                payment_status, liveness_status, decision,
                                reason, tag, image_path, latency_ms)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        claimed, recognized, similarity,
        (user or {}).get('payment_status'),
        liveness_status, decision, reason, tag, evidence, latency_ms,
    ))
    conn.commit()
    conn.close()

    occupant_state = None
    if decision == 'GRANTED' and recognized:
        tracker = OccupancyTracker()
        marked = tracker.mark_inside(recognized)
        occupant_state = 'inside' if marked.get('success') else 'already_inside'

    alert_row_id = None
    if alert_type:
        service = AlertService()
        severity = {
            'PROXY': 'high', 'SPOOF': 'high', 'NOFACE': 'medium',
            'UNKNOWN': 'medium', 'UNPAID': 'medium', 'TAILGATE': 'medium',
        }.get(alert_type, 'medium')
        who = (user or {}).get('name') or claimed or 'unidentified person'
        message = f'{alert_type} at Fab Lab entrance â€” {who}. {reason}'
        alert_row_id = service.save_alert_to_db(alert_type, message,
                                                image_path=evidence,
                                                severity=severity)
        try:
            await service.send_alert(alert_type, message,
                                     image_path=evidence, severity=severity)
            conn = get_connection()
            conn.execute(
                "UPDATE alerts SET sent_status='sent', sent_at=? WHERE id=?",
                (get_current_time_iso(), alert_row_id))
            conn.commit()
            conn.close()
        except Exception as exc:
            logger.error('Telegram send failed: %s', exc)

    return {
        'decision': decision,
        'reason': reason,
        'tag': tag,
        'alert_type': alert_type,
        'alert_id': alert_row_id,
        'user': user,
        'similarity': round(float(similarity), 4),
        'liveness_status': liveness_status,
        'occupant_state': occupant_state,
        'evidence_path': evidence,
        'latency_ms': latency_ms,
        **(extra or {}),
    }


# ------------------------------------------------------------------ #
# Routes
# ------------------------------------------------------------------ #

@router.post('/process')
async def process_entry(request: EntryRequest):
    """Token + Face entry (Mode B, Â§10)."""
    return await _run_pipeline(request, mode='token_face')


@router.post('/face-only')
async def process_face_only(request: EntryRequest):
    """Face-only entry (Mode A, Â§19)."""
    return await _run_pipeline(request, mode='face_only')


@router.post('/simulate')
async def simulate_entry(request: SimulateRequest):
    """Lightweight scenario playback for frontend demos (no CV involved)."""
    scenarios = {
        'authorized': {'decision': 'GRANTED', 'tag': 'authorized', 'reason': 'Authorized entry'},
        'proxy': {'decision': 'DENIED', 'tag': 'proxy', 'reason': 'Proxy attempt detected'},
        'unpaid': {'decision': 'DENIED', 'tag': 'unpaid', 'reason': 'Payment expired'},
        'unknown': {'decision': 'DENIED', 'tag': 'unknown', 'reason': 'Unknown person'},
        'spoof': {'decision': 'DENIED', 'tag': 'spoof', 'reason': 'Spoof detected'},
        'tailgate': {'decision': 'GRANTED', 'tag': 'tailgate', 'reason': 'Multiple faces detected'},
    }
    if request.scenario not in scenarios:
        raise HTTPException(status_code=400, detail=f'Unknown scenario: {request.scenario}')
    return scenarios[request.scenario]

