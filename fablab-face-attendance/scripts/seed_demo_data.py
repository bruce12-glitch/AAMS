#!/usr/bin/env python3
"""
Seed demo data for FacePass FabLab.
Populates database with demo users, logs, alerts, and occupants.
Run: python -m scripts.seed_demo_data
"""

import sys
sys.path.insert(0, '..')

import os

from app.database import get_connection

def main():
    """Seed the database with demo data."""
    from app.security import production_mode
    from app.database import init_db
    if production_mode():
        raise RuntimeError('Demo seeding is disabled in production. Use an empty disposable development database.')
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    
    print("Seeding demo data...")
    
    # Never erase an existing member list, attendance history or credentials.
    for table in ('admin_actions', 'alerts', 'entry_logs', 'occupants', 'tokens', 'users'):
        if cursor.execute(f'SELECT 1 FROM {table} LIMIT 1').fetchone():
            conn.close()
            raise RuntimeError('Refusing to seed a non-empty database; existing data is preserved.')
    
    # 6 Demo users
    users = [
        ('RA2111003010123', 'Rahul Kumar', '9876543210', 'rahul@srmist.edu.in', 'student', 'active', '2026-12-31'),
        ('RA2111003010124', 'Arun S', '9876543211', 'arun@srmist.edu.in', 'student', 'expired', '2025-06-30'),
        ('RA2111003010125', 'Priya M', '9876543212', 'priya@srmist.edu.in', 'student', 'active', '2026-12-31'),
        ('RA2111003010126', 'Deepak R', '9876543213', 'deepak@srmist.edu.in', 'faculty', 'active', '2026-12-31'),
        ('RA2111003010127', 'Meera V', '9876543214', 'meera@srmist.edu.in', 'student', 'active', '2026-12-31'),
        ('RA2111003010128', 'Karthik N', '9876543215', 'karthik@srmist.edu.in', 'student', 'pending', '2026-12-31'),
    ]
    
    # Optional demo sign-in password for all seeded users
    # (console login needs email + password). Set SEED_MEMBER_PASSWORD
    # in the environment to enable it; otherwise seeded users can only
    # sign in after an admin sets their password.
    pwd_hash = None
    seed_password = os.getenv('SEED_MEMBER_PASSWORD', '')
    if seed_password:
        from app.auth import hash_password

        pwd_hash = hash_password(seed_password)

    for user in users:
        cursor.execute('''
            INSERT INTO users (user_id, name, phone, email, user_type, payment_status, payment_expiry, password_hash, active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
        ''', (*user, pwd_hash))

    print(f"[OK] Created {len(users)} users"
          + (" (with demo password)" if pwd_hash else " (no password — set via reset endpoint)"))
    
    # Generate tokens for users
    import time
    for user in users:
        user_id = user[0]
        token_value = f"QR_{user_id}_{int(time.time())}"
        cursor.execute('''
            INSERT INTO tokens (token_value, user_id, token_type, active)
            VALUES (?, ?, 'qr', 1)
        ''', (token_value, user_id))
    
    print("[OK] Created tokens for all users")
    
    # 9 Demo entry logs
    from datetime import datetime, timedelta
    
    now = datetime.now()
    logs = [
        ('RA2111003010123', 'RA2111003010123', 0.89, 'active', 'real', 'GRANTED', 'Authorized entry', 'authorized'),
        ('RA2111003010124', 'RA2111003010124', 0.76, 'expired', 'real', 'DENIED', 'Payment expired', 'unpaid'),
        ('RA2111003010125', 'RA2111003010125', 0.92, 'active', 'real', 'GRANTED', 'Authorized entry', 'authorized'),
        ('RA2111003010123', 'RA2111003010126', 0.34, 'active', 'real', 'DENIED', 'Proxy attempt', 'proxy'),
        (None, None, 0.0, None, 'unknown', 'DENIED', 'Unknown person', 'unknown'),
        ('RA2111003010127', 'RA2111003010127', 0.85, 'active', 'real', 'GRANTED', 'Authorized entry', 'authorized'),
        ('RA2111003010128', 'RA2111003010128', 0.78, 'pending', 'real', 'DENIED', 'Payment pending', 'unpaid'),
        (None, None, 0.0, None, 'spoof', 'DENIED', 'Spoof detected', 'spoof'),
        ('RA2111003010125', 'RA2111003010125', 0.91, 'active', 'real', 'GRANTED', 'Authorized entry', 'authorized'),
    ]
    
    for i, log in enumerate(logs):
        event_time = (now - timedelta(hours=i*2)).isoformat()
        cursor.execute('''
            INSERT INTO entry_logs (event_time, claimed_id, recognized_id, similarity, payment_status, liveness_status, decision, reason, tag, event_source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'sample')
        ''', (event_time, *log))
    
    print(f"[OK] Created {len(logs)} entry logs")
    
    # Sample records must not place fictitious people inside the real lab.
    
    # 5 Demo alerts
    alerts = [
        ('PROXY', 'high', 'Proxy attempt by RA2111003010123 using token of RA2111003010126'),
        ('UNPAID', 'high', 'Unpaid entry attempt by Arun S (payment expired)'),
        ('UNKNOWN', 'medium', 'Unknown person detected at entrance'),
        ('SPOOF', 'high', 'Possible photo attack detected'),
        ('TAILGATE', 'medium', 'Multiple faces detected - possible tailgating'),
    ]
    
    for alert in alerts:
        cursor.execute('''
            INSERT INTO alerts (alert_type, severity, message, sent_status, event_source)
            VALUES (?, ?, ?, 'sample', 'sample')
        ''', alert)
    
    print(f"[OK] Created {len(alerts)} alerts")
    
    # 1 Admin exception
    cursor.execute('''
        INSERT INTO admin_actions (admin_id, action, target_user_id, reason)
        VALUES ('Dr. Meena K.', 'Manual override entry', 'RA2111003010128', 'Student forgot ID card - verified manually')
    ''')
    
    print("[OK] Created 1 admin action")
    
    conn.commit()
    conn.close()
    
    print("\n[OK] Demo data seeded successfully!")

if __name__ == '__main__':
    main()

