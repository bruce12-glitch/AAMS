"""Private Telegram setup, announcements, delivery history and retries."""

from typing import Literal
import hashlib
import re
import secrets
import time
from fastapi import APIRouter, Depends, HTTPException, Request
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
    chat_id: str = Field(default='', max_length=100)
    daily_report_time: str = '20:00'
    timezone: Literal['Asia/Kolkata'] = 'Asia/Kolkata'
    notify_on_enrollment: bool = True
    notify_on_entry: bool = True
    send_photo: bool = True

    @field_validator('chat_id')
    @classmethod
    def valid_chat(cls, value):
        value = value.strip()
        if value and not re.fullmatch(r'-?[1-9]\d{0,19}|@[A-Za-z][A-Za-z0-9_]{4,31}', value):
            raise ValueError('Enter a numeric private/group chat ID or a public group username')
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
async def update_settings(req: SettingsRequest, request: Request, session: dict = Depends(require_admin)):
    from app.notification_settings import save_settings
    current = get_telegram_config()
    if req.enabled and not req.bot_token and not configured(current.get('bot_token')):
        raise HTTPException(status_code=400, detail='A bot token is required for first-time setup')
    save_settings(req.model_dump())
    request.app.state.telegram_pairing = None
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
            if chat.type not in {'private', 'group', 'supergroup'}:
                raise HTTPException(status_code=400, detail='Choose a personal chat or Telegram group')
            title = chat.title or chat.full_name or str(chat.id)
            return {'success': True, 'chat_title': title, 'chat_type': chat.type,
                    'message': 'Chat found. Send a test to verify delivery.'}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=delivery_error(exc)) from None


def pairing_bot():
    """A token alone is enough to pair; no destination has been selected yet."""
    cfg = get_telegram_config()
    if not cfg.get('enabled') or not configured(cfg.get('bot_token')):
        raise HTTPException(status_code=409, detail='Save and enable the bot token first')
    from telegram import Bot
    from telegram.request import HTTPXRequest
    token = str(cfg['bot_token'])
    try:
        bot = Bot(token=token, request=HTTPXRequest(connect_timeout=5, read_timeout=10))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=delivery_error(exc)) from None
    return bot, hashlib.sha256(token.encode()).hexdigest()


@router.post('/pair/start')
async def start_pairing(request: Request, session: dict = Depends(require_admin)):
    if not session:
        raise HTTPException(status_code=401, detail='Sign in as an administrator to pair Telegram')
    bot, fingerprint = pairing_bot()
    try:
        async with bot:
            me = await bot.get_me()
            webhook = await bot.get_webhook_info()
            if webhook.url:
                raise HTTPException(status_code=409, detail='This bot uses a webhook. Enter the chat ID manually or use a dedicated prototype bot; its webhook was preserved.')
        payload = 'aams_' + secrets.token_urlsafe(18)
        request.app.state.telegram_pairing = {
            'payload': payload, 'fingerprint': fingerprint,
            'owner': session['email'], 'created_at': time.time(),
        }
        return {'success': True, 'command': '/start ' + payload,
                'url': f'https://t.me/{me.username}?start={payload}', 'expires_in': 300,
                'message': 'Open Telegram and press Start. Then return here and click Connect this chat within five minutes.'}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=delivery_error(exc)) from None


@router.post('/pair/complete')
async def complete_pairing(request: Request, session: dict = Depends(require_admin)):
    if not session:
        raise HTTPException(status_code=401, detail='Sign in as an administrator to pair Telegram')
    challenge = getattr(request.app.state, 'telegram_pairing', None)
    if not challenge or challenge['owner'] != session['email'] or time.time() - challenge['created_at'] > 300:
        raise HTTPException(status_code=409, detail='Pairing expired or was not started. Click Connect my Telegram again.')
    bot, fingerprint = pairing_bot()
    if fingerprint != challenge['fingerprint']:
        raise HTTPException(status_code=409, detail='The bot token changed. Start pairing again.')
    try:
        async with bot:
            # No offset: do not acknowledge, delete or expose unrelated messages.
            updates = await bot.get_updates(limit=100, timeout=0)
        matches = {
            update.message.chat.id: update.message.chat
            for update in updates
            if update.message and update.message.chat.type == 'private'
            and update.message.date.timestamp() >= challenge['created_at'] - 2
            and update.message.text == '/start ' + challenge['payload']
        }
        if not matches:
            raise HTTPException(status_code=409, detail='Pairing message not found. Open the link, press Start in Telegram, then try Connect this chat again. If another app polls this bot, stop it or enter the chat ID manually.')
        if len(matches) != 1:
            raise HTTPException(status_code=409, detail='The pairing code was used in multiple chats. Start again with a new code.')
        if getattr(request.app.state, 'telegram_pairing', None) is not challenge:
            raise HTTPException(status_code=409, detail='Pairing changed. Start again.')
        from app.notification_settings import save_settings
        chat = next(iter(matches.values()))
        request.app.state.telegram_pairing = None  # One use only.
        save_settings({'chat_id': str(chat.id)})
        return {'success': True, 'chat_title': chat.full_name or str(chat.id),
                'message': 'Personal chat connected. Send a test message to confirm delivery.'}
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
