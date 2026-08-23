"""
Alert Service for FacePass FabLab.
Implements §15 Telegram Bot Integration for real-time alerts.
"""

import logging
from datetime import datetime
from typing import Optional
from app.database import get_connection
from app.config import get_telegram_config

logger = logging.getLogger(__name__)

class AlertService:
    """
    Sends alerts to Telegram group with photo evidence.
    Implements alert formats from §15.2 exactly.
    """
    
    def __init__(self):
        """Initialize alert service with Telegram configuration."""
        config = get_telegram_config()
        self.enabled = config.get('enabled', False)
        self.bot_token = config.get('bot_token', '')
        self.chat_id = config.get('chat_id', '')
        self.send_photo = config.get('send_photo', True)
        
        # Initialize Telegram bot if enabled
        self.bot = None
        if self.enabled and self.bot_token:
            try:
                from telegram import Bot
                self.bot = Bot(token=self.bot_token)
            except Exception as e:
                logger.error(f"Failed to initialize Telegram bot: {e}")
    
    async def send_alert(self, alert_type: str, message: str, 
                        image_path: str = None, severity: str = "high") -> bool:
        """
        Send alert to Telegram group.
        
        Alert formats (§15.2):
        - PROXY ALERT: Location, Claimed ID, Detected Face, Confidence, Time, Photo
        - UNPAID ENTRY ATTEMPT: Name, ID, Payment Expired, Time, Photo
        - UNKNOWN PERSON ALERT: Time, Photo
        - SPOOF ALERT: Possible photo/video used, Time, Photo
        - TAILGATING ALERT: Multiple faces detected, Time, Photo
        - SYSTEM FAULT: Camera offline, Time
        
        Args:
            alert_type: PROXY/UNPAID/UNKNOWN/SPOOF/TAILGATE/NOFACE/SYSTEM
            message: Alert message text
            image_path: Path to evidence photo (optional)
            severity: high/medium/low
            
        Returns:
            True if sent successfully
        """
        if not self.enabled or not self.bot:
            logger.info(f"Alert suppressed (Telegram disabled): {alert_type} - {message}")
            return False
        
        # Low priority alerts go to daily report only
        if severity == "low":
            logger.info(f"Low priority alert logged for daily report: {alert_type}")
            return False
        
        try:
            if self.send_photo and image_path:
                await self.send_with_photo(message, image_path)
            else:
                await self.bot.send_message(chat_id=self.chat_id, text=message)
            
            logger.info(f"Alert sent: {alert_type} - {severity}")
            return True
        except Exception as e:
            logger.error(f"Failed to send Telegram alert: {e}")
            return False
    
    async def send_with_photo(self, caption: str, photo_path: str):
        """Send photo evidence with alert caption."""
        from telegram import InputMediaPhoto
        
        try:
            with open(photo_path, 'rb') as photo:
                await self.bot.send_photo(
                    chat_id=self.chat_id,
                    photo=photo,
                    caption=caption
                )
        except Exception as e:
            logger.error(f"Failed to send photo: {e}")
            # Fallback to text-only
            await self.bot.send_message(chat_id=self.chat_id, text=caption)
    
    async def send_daily_report(self, report_text: str):
        """Send the 8:00 PM daily summary report."""
        if not self.enabled or not self.bot:
            return False
        
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=report_text,
                parse_mode='Markdown'
            )
            logger.info("Daily report sent successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to send daily report: {e}")
            return False
    
    def save_alert_to_db(self, alert_type: str, message: str, 
                        image_path: str = None, severity: str = "medium") -> int:
        """
        Save alert to database for tracking.
        
        Returns:
            Alert ID in database
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO alerts (alert_type, severity, message, image_path, sent_status)
            VALUES (?, ?, ?, ?, 'pending')
        ''', (alert_type, severity, message, image_path))
        
        alert_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return alert_id
    
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
