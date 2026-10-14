"""Private Telegram setup, announcements, delivery history and retries."""

from typing import Literal
import re
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from app.security import require_admin, require_user
from app.config import get_telegram_config
from app.alerts import AlertService, configured, delivery_error

router = APIRouter(prefix='/api/notify', tags=['notify'])


class SendRequest(BaseModel):
    message: str = Field(default='', max_length=1000)


class SettingsRequest(BaseModel):
    enabled: bool = True
    bot_token: str = Field(default='', max_length=200)
    chat_id: str = Field(max_length=100)
    daily_report_time: str = '20:00'
    timezone: Literal['Asia/Kolkata'] = 'Asia/Kolkata'
    notify_on_enrollment: bool = True
    notify_on_entry: bool = True
    send_photo: bool = True

    @field_validator('chat_id')
    @classmethod
    def valid_chat(cls, value):
        value = value.strip()
        if not re.fullmatch(r'-\d{1,20}|@[A-Za-z][A-Za-z0-9_]{4,31}', value):
            raise ValueError('Enter a Telegram group ID (negative number) or public group username')
        return value

    @field_validator('daily_report_time')
    @classmethod
    def valid_time(cls, value):
        if not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', value):
            raise ValueError('Use a 24-hour time, HH:MM')
        return value

    @field_validator('bot_token')
    @classmethod
    def valid_token(cls, value):
        value = value.strip()
        if value and not re.fullmatch(r'\d+:[A-Za-z0-9_-]{20,}', value):
            raise ValueError('Enter a valid bot token from BotFather')
        return value


@router.get('/status')
async def notify_status(session: dict = Depends(require_user)):
    cfg = get_telegram_config()
    result = {
        'telegram_enabled': bool(cfg.get('enabled')),
        'bot_configured': configured(cfg.get('bot_token')),
        'chat_configured': configured(cfg.get('chat_id')),
        'daily_report_time': cfg['daily_report_time'], 'timezone': cfg['timezone'],
        'notify_on_enrollment': cfg['notify_on_enrollment'],
        'notify_on_entry': cfg['notify_on_entry'], 'send_photo': cfg['send_photo'],
    }
    if session.get('role') == 'admin':
        result['chat_id'] = str(cfg.get('chat_id') or '') if configured(cfg.get('chat_id')) else ''
    from app.database import get_connection
    conn = get_connection()
    try:
        result['pending_count'] = conn.execute("SELECT COUNT(*) FROM alerts WHERE sent_status IN ('pending','sending')").fetchone()[0]
        result['last_sent_at'] = conn.execute("SELECT MAX(sent_at) FROM alerts WHERE sent_status='sent'").fetchone()[0]
    finally:
        conn.close()
    return result


@router.put('/settings')
async def update_settings(req: SettingsRequest, session: dict = Depends(require_admin)):
    from app.notification_settings import save_settings
    current = get_telegram_config()
    if req.enabled and not req.bot_token and not configured(current.get('bot_token')):
        raise HTTPException(status_code=400, detail='A bot token is required for first-time setup')
    save_settings(req.model_dump())
    from app.main import app
    scheduler = getattr(app.state, 'report_scheduler', None)
    if scheduler and scheduler.scheduler.running:
        scheduler.reschedule_daily_report()
    return {'success': True, 'message': 'Telegram settings saved. Credentials remain private.'}


@router.post('/verify')
async def verify_destination(_: dict = Depends(require_admin)):
    service = AlertService()
    if not service.bot:
        raise HTTPException(status_code=409, detail='Configure and enable Telegram first')
    try:
        async with service.bot:
            chat = await service.bot.get_chat(service.chat_id)
            if chat.type not in {'group', 'supergroup'}:
                raise HTTPException(status_code=400, detail='The configured destination must be a Telegram group')
            return {'success': True, 'group_title': chat.title, 'message': 'Group found. Send a test to verify posting permission.'}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=delivery_error(exc)) from None


@router.post('/send')
async def send_announcement(req: SendRequest, _: dict = Depends(require_admin)):
    text = req.message.strip()
    if not text:
        raise HTTPException(status_code=400, detail='Message is empty')
    result = await AlertService().queue_and_deliver('ANNOUNCE', text)
    return {'success': True, **result}


@router.post('/test')
async def send_test(_: dict = Depends(require_admin)):
    result = await AlertService().queue_and_deliver('TEST', 'AAMS connection test: Fab Lab student updates, entry alerts and daily summaries are enabled.')
    return {'success': True, **result}


@router.post('/daily-report')
async def send_daily_report(_: dict = Depends(require_admin)):
    from app.reports import ReportGenerator
    generator = ReportGenerator()
    result = await AlertService().queue_and_deliver('REPORT', generator.to_plain_text(generator.generate_daily()))
    return {'success': True, **result}


@router.get('/history')
async def history(_: dict = Depends(require_admin)):
    from app.database import get_connection
    conn = get_connection()
    try:
        rows = conn.execute('SELECT id, alert_type, message, created_at, sent_at, sent_status, delivery_attempts, last_error FROM alerts ORDER BY id DESC LIMIT 50').fetchall()
        return {'notifications': [dict(row) for row in rows]}
    finally:
        conn.close()


@router.post('/retry')
async def retry_pending(_: dict = Depends(require_admin)):
    count = await AlertService().flush_pending()
    return {'success': True, 'delivered': count, 'message': 'Recent attempts wait at least one minute before retry.'}
