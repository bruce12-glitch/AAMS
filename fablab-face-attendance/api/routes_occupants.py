"""
Occupants API Routes for FacePass FabLab.
Implements GET occupants, POST checkout.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.security import require_admin

router = APIRouter(prefix='/api/occupants', tags=['occupants'])

@router.get('')
async def list_occupants():
    """List current occupants inside the Fab Lab."""
    from app.occupancy import OccupancyTracker
    
    tracker = OccupancyTracker()
    occupants = tracker.get_current_occupants()
    
    return {'occupants': occupants, 'count': len(occupants)}

@router.post('/{user_id}/exit')
async def mark_exit(user_id: str, _: None = Depends(require_admin)):
    """Mark user as exited (admin token — otherwise anyone could empty the room)."""
    from app.occupancy import OccupancyTracker
    
    tracker = OccupancyTracker()
    result = tracker.mark_exit(user_id)
    
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['reason'])
    
    return result

@router.post('/scan')
async def trigger_scan(_: None = Depends(require_admin)):
    """Trigger indoor floor scan simulation."""
    # This would integrate with indoor positioning system
    return {'success': True, 'message': 'Scan triggered'}
