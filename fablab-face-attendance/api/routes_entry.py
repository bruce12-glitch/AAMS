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
    Simulate entry scenarios for frontend demo.
    """
    scenarios = {
        'authorized': {'decision': 'GRANTED', 'tag': 'authorized', 'reason': 'Authorized entry'},
        'proxy': {'decision': 'DENIED', 'tag': 'proxy', 'reason': 'Proxy attempt detected'},
        'unpaid': {'decision': 'DENIED', 'tag': 'unpaid', 'reason': 'Payment expired'},
        'unknown': {'decision': 'DENIED', 'tag': 'unknown', 'reason': 'Unknown person'},
        'spoof': {'decision': 'DENIED', 'tag': 'spoof', 'reason': 'Spoof detected'},
        'tailgate': {'decision': 'GRANTED', 'tag': 'tailgate', 'reason': 'Multiple faces detected'}
    }
    
    if request.scenario not in scenarios:
        raise HTTPException(status_code=400, detail=f'Unknown scenario: {request.scenario}')
    
    return scenarios[request.scenario]
