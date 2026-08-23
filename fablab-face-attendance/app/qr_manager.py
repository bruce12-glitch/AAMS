"""
QR Security Manager for FacePass FabLab.
Implements §27.3 Signed QR Code generation and verification.
"""

import hmac
import hashlib
import json
import time
import qrcode
from io import BytesIO
from app.config import get_security_config

class QRManager:
    """
    Generates and verifies signed QR tokens for secure access.
    """
    
    def __init__(self):
        """Initialize QR manager with secret key."""
        config = get_security_config()
        self.secret_key = config.get('qr_secret_key', 'default_secret_change_me')
    
    def _generate_signature(self, payload: dict) -> str:
        """Generate HMAC-SHA256 signature for payload."""
        # Create message without signature
        msg = json.dumps({
            'user_id': payload['user_id'],
            'issued_at': payload['issued_at'],
            'expires_at': payload['expires_at']
        }, sort_keys=True)
        
        signature = hmac.new(
            self.secret_key.encode(),
            msg.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    def generate_token(self, user_id: str, ttl_seconds: int = 86400) -> dict:
        """
        Generate signed QR payload.
        
        Args:
            user_id: User's unique ID
            ttl_seconds: Time-to-live in seconds (default 24 hours)
            
        Returns:
            Dictionary with user_id, issued_at, expires_at, signature
        """
        issued_at = int(time.time())
        expires_at = issued_at + ttl_seconds
        
        payload = {
            'user_id': user_id,
            'issued_at': issued_at,
            'expires_at': expires_at
        }
        
        signature = self._generate_signature(payload)
        payload['signature'] = signature
        
        return payload
    
    def verify_token(self, token_json: str) -> dict:
        """
        Verify signature and expiry of a QR token.
        
        Args:
            token_json: JSON string of the token payload
            
        Returns:
            Dictionary with valid: bool, user_id: str, reason: str
        """
        try:
            token = json.loads(token_json)
        except json.JSONDecodeError:
            return {'valid': False, 'user_id': None, 'reason': 'Invalid JSON format'}
        
        # Check required fields
        required = ['user_id', 'issued_at', 'expires_at', 'signature']
        for field in required:
            if field not in token:
                return {'valid': False, 'user_id': None, 'reason': f'Missing field: {field}'}
        
        # Check expiry
        current_time = int(time.time())
        if current_time > token['expires_at']:
            return {'valid': False, 'user_id': token.get('user_id'), 'reason': 'Token expired'}
        
        # Verify signature
        expected_sig = self._generate_signature(token)
        if not hmac.compare_digest(token['signature'], expected_sig):
            return {'valid': False, 'user_id': token.get('user_id'), 'reason': 'Invalid signature'}
        
        return {'valid': True, 'user_id': token['user_id'], 'reason': 'Valid token'}
    
    def generate_qr_image(self, user_id: str, ttl_seconds: int = 86400) -> bytes:
        """
        Generate QR code image as PNG bytes.
        
        Args:
            user_id: User's unique ID
            ttl_seconds: Token time-to-live
            
        Returns:
            PNG image bytes
        """
        token = self.generate_token(user_id, ttl_seconds)
        token_json = json.dumps(token)
        
        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4
        )
        qr.add_data(token_json)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to bytes
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()
