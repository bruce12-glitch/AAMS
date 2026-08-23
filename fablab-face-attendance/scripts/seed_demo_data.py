#!/usr/bin/env python3
"""
Seed demo data for FacePass FabLab.
Populates database with demo users, logs, alerts, and occupants.
Run: python -m scripts.seed_demo_data
"""

import sys
sys.path.insert(0, '..')

import numpy as np
from app.database import get_connection

def generate_random_embedding() -> bytes:
    """Generate a random normalized 512-d embedding."""
    emb = np.random.randn(512)
    emb = emb / np.linalg.norm(emb)
    return emb.tobytes()

def main():
    """Seed the database with demo data."""
    conn = get_connection()
    cursor = conn.cursor()
    
    print("Seeding demo data...")
    
    # Clear existing data
    cursor.execute('DELETE FROM admin_actions')
    cursor.execute('DELETE FROM alerts')
    cursor.execute('DELETE FROM entry_logs')
    cursor.execute('DELETE FROM occupants')
    cursor.execute('DELETE FROM tokens')
    cursor.execute('DELETE FROM users')
    
    # 6 Demo users
    users = [
        ('RA2111003010123', 'Rahul Kumar', '9876543210', 'rahul@srmist.edu.in', 'student', 'active', '2026-12-31'),
        ('RA2111003010124', 'Arun S', '9876543211', 'arun@srmist.edu.in', 'student', 'expired', '2025-06-30'),
        ('RA2111003010125', 'Priya M', '9876543212', 'priya@srmist.edu.in', 'student', 'active', '2026-12-31'),
        ('RA2111003010126', 'Deepak R', '9876543213', 'deepak@srmist.edu.in', 'faculty', 'active', '2026-12-31'),
        ('RA2111003010127', 'Meera V', '9876543214', 'meera@srmist.edu.in', 'student', 'active', '2026-12-31'),
        ('RA2111003010128', 'Karthik N', '9876543215', 'karthik@srmist.edu.in', 'student', 'pending', '2026-12-31'),
    ]
    
    for user in users:
        embedding = generate_random_embedding()
        cursor.execute('''
            INSERT INTO users (user_id, name, phone, email, user_type, payment_status, payment_expiry, face_embedding)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (*user, embedding))
    
    print(f"✓ Created {len(users)} users")
    
    # Generate tokens for users
    import time
    for user in users:
        user_id = user[0]
        token_value = f"QR_{user_id}_{int(time.time())}"
        cursor.execute('''
            INSERT INTO tokens (token_value, user_id, token_type, active)
            VALUES (?, ?, 'qr', 1)
        ''', (token_value, user_id))
    
    print("✓ Created tokens for all users")
    
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
            INSERT INTO entry_logs (event_time, claimed_id, recognized_id, similarity, payment_status, liveness_status, decision, reason, tag)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (event_time, *log))
    
    print(f"✓ Created {len(logs)} entry logs")
    
    # 5 Demo occupants (3 inside, 2 exited)
    occupants = [
        ('RA2111003010123', 'inside'),
        ('RA2111003010125', 'inside'),
        ('RA2111003010127', 'inside'),
        ('RA2111003010124', 'exited'),
        ('RA2111003010126', 'exited'),
    ]
    
    for occ in occupants:
        entry_time = (now - timedelta(hours=3)).isoformat()
        exit_time = (now - timedelta(hours=1)).isoformat() if occ[1] == 'exited' else None
        cursor.execute('''
            INSERT INTO occupants (user_id, entry_time, last_seen_time, exit_time, status)
            VALUES (?, ?, ?, ?, ?)
        ''', (occ[0], entry_time, entry_time, exit_time, occ[1]))
    
    print(f"✓ Created {len(occupants)} occupancy records")
    
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
            INSERT INTO alerts (alert_type, severity, message, sent_status)
            VALUES (?, ?, ?, 'sent')
        ''', alert)
    
    print(f"✓ Created {len(alerts)} alerts")
    
    # 1 Admin exception
    cursor.execute('''
        INSERT INTO admin_actions (admin_id, action, target_user_id, reason)
        VALUES ('Dr. Meena K.', 'Manual override entry', 'RA2111003010128', 'Student forgot ID card - verified manually')
    ''')
    
    print("✓ Created 1 admin action")
    
    conn.commit()
    conn.close()
    
    print("\n✓ Demo data seeded successfully!")

if __name__ == '__main__':
    main()
