"""Telegram transport and a durable, auditable delivery queue."""

import logging
from datetime import datetime, timezone
from pathlib import Path

from app.database import get_connection
from app.config import get_telegram_config, BASE_DIR

logger = logging.getLogger(__name__)


def configured(value):
    text = str(value or '').strip()
    return bool(text) and text.lower() not in {'skip', 'none', 'null'} and not text.startswith(('YOUR_', 'CHANGE_'))


def delivery_error(exc):
    # Telegram/network exceptions may contain request URLs with bot tokens.
    names = {
        'Forbidden': 'Bot cannot post to the group. Add it and allow messages.',
        'InvalidToken': 'The Telegram bot token is invalid.',
        'BadRequest': 'Telegram rejected the destination or message. Check the group ID.',
        'TimedOut': 'Telegram timed out; the message remains queued for retry.',
        'NetworkError': 'Telegram is unreachable; the message remains queued for retry.',
        'RetryAfter': 'Telegram rate limit reached; the message remains queued for retry.',
    }
    return names.get(type(exc).__name__, 'Telegram delivery failed; check bot permissions and connection.')


class AlertService:
    def __init__(self):
        config = get_telegram_config()
        self.enabled = bool(config.get('enabled', False))
        self.bot_token = str(config.get('bot_token') or '')
        self.chat_id = str(config.get('chat_id') or '')
        self.send_photo = bool(config.get('send_photo', True))
        self.bot = None
        if self.enabled and configured(self.bot_token) and configured(self.chat_id):
            try:
                from telegram import Bot
                from telegram.request import HTTPXRequest
                self.bot = Bot(token=self.bot_token, request=HTTPXRequest(
                    connect_timeout=5, read_timeout=10, write_timeout=10, pool_timeout=5))
            except Exception as exc:
                logger.warning('Telegram initialization failed (%s)', type(exc).__name__)

    async def _send(self, text, image_path=None):
        if not self.enabled or not self.bot:
            return False, 'Telegram is not configured. Message is queued.'
        try:
            async with self.bot:
                path = (BASE_DIR / image_path).resolve() if image_path else None
                image_root = (BASE_DIR / 'images').resolve()
                if self.send_photo and path and path.is_relative_to(image_root) and path.is_file():
                    try:
                        with path.open('rb') as photo:
                            await self.bot.send_photo(chat_id=self.chat_id, photo=photo, caption=text[:1024])
                        if len(text) > 1024:
                            await self.bot.send_message(chat_id=self.chat_id, text=text[1024:4096])
                    except Exception:
                        await self.bot.send_message(chat_id=self.chat_id, text=text[:4096])
                else:
                    await self.bot.send_message(chat_id=self.chat_id, text=text[:4096])
            return True, 'Delivered to Telegram'
        except Exception as exc:
            logger.warning('Telegram send failed (%s)', type(exc).__name__)
            return False, delivery_error(exc)

    async def send_alert(self, alert_type, message, image_path=None, severity='high'):
        if severity == 'low':
            return False
        sent, _reason = await self._send(message, image_path)
        return sent

    async def send_with_photo(self, caption, photo_path):
        return await self._send(caption, photo_path)

    async def send_announcement(self, message):
        text = (message or '').strip()
        if not text:
            return False, 'Message is empty'
        return await self._send(text)

    async def send_daily_report(self, report_text):
        # Plain text avoids Markdown parse errors caused by names/punctuation.
        return (await self._send(report_text))[0]

    def save_alert_to_db(self, alert_type, message, image_path=None, severity='medium', dedupe_key=None):
        conn = get_connection()
        try:
            cur = conn.execute('''
                INSERT OR IGNORE INTO alerts (alert_type, severity, message, image_path, sent_status, dedupe_key)
                VALUES (?, ?, ?, ?, 'pending', ?)
            ''', (alert_type, severity, message, image_path, dedupe_key))
            alert_id = cur.lastrowid
            if cur.rowcount == 0:
                alert_id = conn.execute('SELECT id FROM alerts WHERE dedupe_key=?', (dedupe_key,)).fetchone()[0]
            conn.commit()
            return alert_id
        finally:
            conn.close()

    async def deliver(self, alert_id):
        if not self.enabled or not self.bot:
            return False, 'Telegram is not configured. Message is queued.'
        conn = get_connection()
        try:
            # Atomic claim prevents scheduler/manual retry races in one host.
            cur = conn.execute("UPDATE alerts SET sent_status='sending', delivery_attempts=delivery_attempts+1, last_attempt_at=datetime('now') WHERE id=? AND sent_status='pending'", (alert_id,))
            conn.commit()
            row = conn.execute('SELECT * FROM alerts WHERE id=?', (alert_id,)).fetchone()
            if not row:
                return False, 'Notification not found'
            if cur.rowcount == 0:
                return row['sent_status'] == 'sent', 'Already delivered' if row['sent_status'] == 'sent' else 'Delivery is already in progress'
        finally:
            conn.close()
        if row['severity'] == 'low' and row['alert_type'] not in {'ANNOUNCE', 'REPORT', 'ENROLLMENT', 'ENTRY', 'TEST'}:
            sent, reason = False, 'Included in daily summary only'
            status = 'suppressed'
        else:
            sent, reason = await self._send(row['message'], row['image_path'])
            status = 'sent' if sent else 'pending'
        conn = get_connection()
        try:
            conn.execute('UPDATE alerts SET sent_status=?, sent_at=?, last_error=? WHERE id=?', (
                status, datetime.now(timezone.utc).isoformat() if sent else None,
                None if sent else reason, alert_id))
            conn.commit()
        finally:
            conn.close()
        return sent, reason

    async def queue_and_deliver(self, alert_type, message, severity='low', image_path=None, dedupe_key=None):
        alert_id = self.save_alert_to_db(alert_type, message, image_path, severity, dedupe_key)
        sent, reason = await self.deliver(alert_id)
        return {'alert_id': alert_id, 'telegram_sent': sent, 'reason': reason}

    async def flush_pending(self, max_age_hours=24):
        if not self.enabled or not self.bot:
            return 0
        conn = get_connection()
        try:
            # Recover claims abandoned by a stopped process. Telegram has no
            # idempotency key: ambiguous network outcomes can be redelivered.
            conn.execute("UPDATE alerts SET sent_status='pending' WHERE sent_status='sending' AND datetime(last_attempt_at)<datetime('now','-5 minutes')")
            conn.execute("UPDATE alerts SET sent_status='expired' WHERE sent_status='pending' AND datetime(created_at)<datetime('now',?)", (f'-{int(max_age_hours)} hours',))
            rows = conn.execute("SELECT id FROM alerts WHERE sent_status='pending' AND (last_attempt_at IS NULL OR datetime(last_attempt_at)<=datetime('now','-1 minute')) ORDER BY id LIMIT 50").fetchall()
            conn.commit()
        finally:
            conn.close()
        delivered = 0
        for row in rows:
            sent, _reason = await self.deliver(row['id'])
            delivered += int(sent)
        return delivered

    def format_proxy_alert(self, location: str, claimed_id: str, 
                          detected_face: str, confidence: float, 
                          time_str: str, photo_path: str = None) -> tuple:
        """Format PROXY alert message per §15.2."""
        message = (
            f"🚨 *PROXY ALERT*\n\n"
            f"📍 Location: {location}\n"
            f"🆔 Claimed ID: {claimed_id}\n"
            f"👤 Detected Face: {detected_face}\n"
            f"📊 Confidence: {confidence:.2f}\n"
            f"⏰ Time: {time_str}"
        )
        return message, "high"
    
    def format_unpaid_alert(self, name: str, user_id: str, 
                           payment_expired: str, time_str: str,
                           photo_path: str = None) -> tuple:
        """Format UNPAID ENTRY ATTEMPT alert message per §15.2."""
        message = (
            f"💰 *UNPAID ENTRY ATTEMPT*\n\n"
            f"👤 Name: {name}\n"
            f"🆔 ID: {user_id}\n"
            f"❌ Payment Expired: {payment_expired}\n"
            f"⏰ Time: {time_str}"
        )
        return message, "high"
    
    def format_unknown_alert(self, time_str: str, photo_path: str = None) -> tuple:
        """Format UNKNOWN PERSON ALERT message per §15.2."""
        message = (
            f"❓ *UNKNOWN PERSON ALERT*\n\n"
            f"⏰ Time: {time_str}\n"
            f"📸 Photo evidence attached"
        )
        return message, "medium"
    
    def format_spoof_alert(self, description: str, time_str: str,
                          photo_path: str = None) -> tuple:
        """Format SPOOF ALERT message per §15.2."""
        message = (
            f"⚠️ *SPOOF ALERT*\n\n"
            f"🎭 Possible photo/video attack: {description}\n"
            f"⏰ Time: {time_str}"
        )
        return message, "high"
    
    def format_tailgate_alert(self, face_count: int, time_str: str,
                              photo_path: str = None) -> tuple:
        """Format TAILGATING ALERT message per §15.2."""
        message = (
            f"🚪 *TAILGATING ALERT*\n\n"
            f"👥 Multiple faces detected: {face_count}\n"
            f"⏰ Time: {time_str}"
        )
        return message, "medium"
    
    def format_system_fault(self, fault_description: str, time_str: str) -> tuple:
        """Format SYSTEM FAULT alert message per §15.2."""
        message = (
            f"🔧 *SYSTEM FAULT*\n\n"
            f"❌ {fault_description}\n"
            f"⏰ Time: {time_str}"
        )
        return message, "high"
