"""HMAC QR tokens — no camera required."""

import json
import time

from app.qr_manager import QRManager


def test_roundtrip_valid():
    qr = QRManager()
    token = qr.generate_token("RA2111003010123", ttl_seconds=60)
    result = qr.verify_token(json.dumps(token))
    assert result["valid"] is True
    assert result["user_id"] == "RA2111003010123"


def test_tampered_signature():
    qr = QRManager()
    token = qr.generate_token("RA2111003010123", ttl_seconds=60)
    token["user_id"] = "RA0000000000000"
    result = qr.verify_token(json.dumps(token))
    assert result["valid"] is False


def test_expired():
    qr = QRManager()
    token = qr.generate_token("RA2111003010123", ttl_seconds=1)
    token["expires_at"] = int(time.time()) - 10
    # resign so expiry is the only failure
    token["signature"] = qr._generate_signature(token)
    result = qr.verify_token(json.dumps(token))
    assert result["valid"] is False
    assert "expired" in result["reason"].lower()
