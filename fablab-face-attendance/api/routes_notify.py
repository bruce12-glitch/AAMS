"""
Communication portal — send Telegram messages from the console.

GET  /api/notify/status  — Telegram wiring state (side-effect free)
POST /api/notify/send    — send an announcement (admin-guarded).
  Body: { "message": "text up to 1000 chars" }
  The announcement is always stored in the alerts table (audit trail);
  Telegram delivery is attempted and its outcome reported honestly —
  with demo/placeholder credentials it stores without sending.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.security import require_admin

router = APIRouter(prefix='/api/notify', tags=['notify'])

MAX_LEN = 1000


class SendRequest(BaseModel):
    message: str = ''


@router.get('/status')
async def notify_status():
    """Telegram wiring state for the Communicate page."""
    from app.config import get_telegram_config

    cfg = get_telegram_config()
    tok = str(cfg.get('bot_token') or '')
    chat = str(cfg.get('chat_id') or '')
    tok_low = tok.lower()
    return {
        'telegram_enabled': bool(cfg.get('enabled', False)),
        'bot_configured': bool(tok) and 'here' not in tok_low
        and tok_low not in ('skip', 'none', 'null')
        and not tok.startswith('YOUR_'),
        'chat_configured': bool(chat) and not chat.startswith('YOUR_') and chat != 'skip',
    }


@router.post('/send')
async def send_announcement(req: SendRequest, _: None = Depends(require_admin)):
    """Store + deliver a console announcement via Telegram."""
    from app.alerts import AlertService

    text = (req.message or '').strip()
    if not text:
        raise HTTPException(status_code=400, detail='Message is empty')
    if len(text) > MAX_LEN:
        raise HTTPException(status_code=400, detail=f'Message exceeds {MAX_LEN} characters')

    service = AlertService()
    alert_id = service.save_alert_to_db('ANNOUNCE', text, severity='low')
    sent, reason = await service.send_announcement(text)

    from app.database import get_connection
    from datetime import datetime
    if sent:
        conn = get_connection()
        conn.execute(
            "UPDATE alerts SET sent_status='sent', sent_at=? WHERE id=?",
            (datetime.now().isoformat(), alert_id))
        conn.commit()
        conn.close()

    return {'success': True, 'alert_id': alert_id, 'telegram_sent': sent, 'reason': reason}
