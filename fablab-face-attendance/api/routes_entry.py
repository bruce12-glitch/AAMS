"""
Entry Processing API Routes for FacePass FabLab.
Implements POST /api/entry/process, /api/entry/face-only, /api/entry/simulate
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/api/entry', tags=['entry'])

class EntryRequest(BaseModel):
    token_value: Optional[str] = None
    face_embedding: Optional[list] = None
    liveness_status: str = 'unknown'
    face_count: int = 1

class SimulateRequest(BaseModel):
    scenario: str  # authorized/proxy/unpaid/unknown/spoof/tailgate

@router.post('/process')
async def process_entry(request: EntryRequest):
    """
    Process entry with token + face (Mode B).
    Implements full decision matrix from §11.2.
    """
    from app.identity import IdentityVerifier
    from app.access_policy import AccessDecision
    from app.database import get_connection
    from app.utils import get_current_time_iso
    
    if not request.token_value:
        raise HTTPException(status_code=400, detail='Token value required')
    
    verifier = IdentityVerifier()
    policy = AccessDecision()
    
    # Convert embedding list to numpy array
    import numpy as np
    face_embedding = np.array(request.face_embedding) if request.face_embedding else None
    
    if face_embedding is None:
        return {
            'decision': 'DENIED',
            'reason': 'No face provided',
            'tag': 'noface'
        }
    
    # Verify token + face
    result = verifier.verify_token_face(request.token_value, face_embedding)
    
    # Get payment status
    payment_status = 'inactive'
    if result.get('claimed_user'):
        payment_status = result['claimed_user'].get('payment_status', 'inactive')
    
    # Evaluate access
    decision = policy.evaluate_access(
        claimed_id=request.token_value,
        face_result=result,
        payment_status=payment_status,
        liveness_status=request.liveness_status,
        face_count=request.face_count
    )
    
    # Log entry attempt
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO entry_logs (claimed_id, recognized_id, similarity, payment_status, liveness_status, decision, reason, tag)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        request.token_value,
        result.get('detected_user'),
        result.get('similarity', 0),
        payment_status,
        request.liveness_status,
        decision['decision'],
        decision['reason'],
        decision['tag']
    ))
    conn.commit()
    conn.close()
    
    logger.info(f"Entry processed: {decision['decision']} - {decision['tag']}")
    
    return {
        'decision': decision['decision'],
        'reason': decision['reason'],
        'tag': decision['tag'],
        'alert_type': decision['alert_type'],
        'user': result.get('claimed_user') or result.get('user')
    }

@router.post('/face-only')
async def process_face_only(request: EntryRequest):
    """
    Process entry with face only (Mode A - §19).
    """
    from app.identity import IdentityVerifier
    from app.access_policy import AccessDecision
    import numpy as np
    
    verifier = IdentityVerifier()
    policy = AccessDecision()
    
    face_embedding = np.array(request.face_embedding) if request.face_embedding else None
    
    if face_embedding is None:
        return {'decision': 'DENIED', 'reason': 'No face provided', 'tag': 'noface'}
    
    result = verifier.verify_face_only(face_embedding)
    
    payment_status = 'inactive'
    if result.get('user'):
        payment_status = result['user'].get('payment_status', 'inactive')
    
    decision = policy.evaluate_access(
        claimed_id=None,
        face_result=result,
        payment_status=payment_status,
        liveness_status=request.liveness_status,
        face_count=request.face_count
    )
    
    return {
        'decision': decision['decision'],
        'reason': decision['reason'],
        'tag': decision['tag'],
        'user': result.get('user')
    }

@router.post('/simulate')
async def simulate_entry(request: SimulateRequest):
    """
    Simulate entry scenarios for the live console.

    Persists a matching entry_log (and occupancy / alert when relevant)
    so the dashboard updates without a camera.
    """
    from datetime import datetime
    from app.database import get_connection
    from app.occupancy import OccupancyTracker

    scenarios = {
        'authorized': {
            'decision': 'GRANTED', 'tag': 'authorized', 'reason': 'Token + face verified',
            'alert_type': None, 'claimed_id': 'RA2111003010123',
            'recognized_id': 'RA2111003010123', 'similarity': 0.74,
            'payment_status': 'active', 'liveness_status': 'real',
            'name': 'Rahul Kumar',
        },
        'proxy': {
            'decision': 'DENIED', 'tag': 'proxy', 'reason': 'Identity mismatch — proxy attempt',
            'alert_type': 'PROXY', 'claimed_id': 'RA2111003010123',
            'recognized_id': 'RA2111003010124', 'similarity': 0.21,
            'payment_status': 'active', 'liveness_status': 'real',
            'name': 'Arun S',
        },
        'unpaid': {
            'decision': 'DENIED', 'tag': 'unpaid', 'reason': 'Payment expired',
            'alert_type': 'UNPAID', 'claimed_id': 'RA2111003010124',
            'recognized_id': 'RA2111003010124', 'similarity': 0.66,
            'payment_status': 'expired', 'liveness_status': 'real',
            'name': 'Arun S',
        },
        'unknown': {
            'decision': 'DENIED', 'tag': 'unknown', 'reason': 'Face not in database',
            'alert_type': 'UNKNOWN', 'claimed_id': None,
            'recognized_id': None, 'similarity': 0.18,
            'payment_status': None, 'liveness_status': 'real',
            'name': 'Unknown Person',
        },
        'spoof': {
            'decision': 'DENIED', 'tag': 'spoof', 'reason': 'Liveness failed — no blink',
            'alert_type': 'SPOOF', 'claimed_id': 'RA2111003010125',
            'recognized_id': 'RA2111003010125', 'similarity': 0.61,
            'payment_status': 'active', 'liveness_status': 'spoof',
            'name': 'Priya M',
        },
        'tailgate': {
            'decision': 'GRANTED', 'tag': 'tailgate', 'reason': 'Granted • 2 faces flagged',
            'alert_type': 'TAILGATE', 'claimed_id': 'RA2111003010125',
            'recognized_id': 'RA2111003010125', 'similarity': 0.69,
            'payment_status': 'active', 'liveness_status': 'real',
            'name': 'Priya M',
        },
        'noface': {
            'decision': 'DENIED', 'tag': 'noface', 'reason': 'No face detected',
            'alert_type': 'NOFACE', 'claimed_id': 'RA2111003010123',
            'recognized_id': None, 'similarity': 0.0,
            'payment_status': 'active', 'liveness_status': 'unknown',
            'name': None,
        },
    }

    if request.scenario not in scenarios:
        raise HTTPException(status_code=400, detail=f'Unknown scenario: {request.scenario}')

    sc = scenarios[request.scenario]
    now = datetime.now().isoformat()

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''
        INSERT INTO entry_logs
            (event_time, claimed_id, recognized_id, similarity, payment_status,
             liveness_status, decision, reason, tag)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''',
        (
            now, sc['claimed_id'], sc['recognized_id'], sc['similarity'],
            sc['payment_status'], sc['liveness_status'], sc['decision'],
            sc['reason'], sc['tag'],
        ),
    )

    if sc['alert_type']:
        cursor.execute(
            '''
            INSERT INTO alerts (alert_type, severity, message, sent_status)
            VALUES (?, ?, ?, 'pending')
            ''',
            (
                sc['alert_type'],
                'high' if sc['alert_type'] in ('PROXY', 'SPOOF', 'SYSTEM') else 'medium',
                f"{sc['alert_type']} — {sc['reason']}",
            ),
        )

    conn.commit()
    conn.close()

    if sc['decision'] == 'GRANTED' and sc['recognized_id']:
        tracker = OccupancyTracker()
        result = tracker.mark_inside(sc['recognized_id'])
        if not result.get('success'):
            tracker.update_last_seen(sc['recognized_id'])

    logger.info(f"Simulated {request.scenario}: {sc['decision']} / {sc['tag']}")
    return {
        'decision': sc['decision'],
        'reason': sc['reason'],
        'tag': sc['tag'],
        'alert_type': sc['alert_type'],
        'name': sc['name'],
        'similarity': sc['similarity'],
        'persisted': True,
    }
