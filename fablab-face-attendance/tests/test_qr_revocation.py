"""QR passes are unique and revocation is backed by SQLite state."""

from fastapi.testclient import TestClient

from app.main import app
from app.qr_manager import QRManager


def test_qr_tokens_are_unique_and_tamper_evident():
    qr = QRManager()
    first = qr.generate_token('QR-PROBE')
    second = qr.generate_token('QR-PROBE')
    assert first['token_id'] != second['token_id']
    encoded = qr.serialize_token(first)
    assert qr.verify_token(encoded)['valid'] is True
    assert qr.verify_token(encoded.replace('QR-PROBE', 'QR-OTHER'))['valid'] is False


def test_rekey_removes_the_old_active_pass():
    from app.database import get_connection, init_db

    init_db()
    conn = get_connection()
    conn.execute('DELETE FROM tokens WHERE user_id=?', ('QRPROBE001',))
    conn.execute('DELETE FROM users WHERE user_id=?', ('QRPROBE001',))
    conn.execute(
        "INSERT INTO users (user_id, name, email, active) VALUES (?, ?, ?, 1)",
        ('QRPROBE001', 'QR Probe', 'qrprobe@srmist.edu.in'))
    conn.commit()
    conn.close()

    client = TestClient(app, raise_server_exceptions=False)
    try:
        first = client.post('/api/users/QRPROBE001/tokens/revoke').json()['token']
        second = client.post('/api/users/QRPROBE001/tokens/revoke').json()['token']
        assert first['token_id'] != second['token_id']

        qr = QRManager()
        conn = get_connection()
        rows = conn.execute(
            'SELECT token_value FROM tokens WHERE user_id=? AND active=1',
            ('QRPROBE001',)).fetchall()
        conn.close()
        assert [row['token_value'] for row in rows] == [qr.serialize_token(second)]
        assert qr.serialize_token(first) not in [row['token_value'] for row in rows]
    finally:
        conn = get_connection()
        conn.execute('DELETE FROM tokens WHERE user_id=?', ('QRPROBE001',))
        conn.execute('DELETE FROM users WHERE user_id=?', ('QRPROBE001',))
        conn.commit()
        conn.close()
