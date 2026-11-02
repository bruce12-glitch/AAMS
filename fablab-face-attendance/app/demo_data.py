"""Explicit, additive showcase examples. Never fabricate biometric enrollment."""
from app.database import get_connection


def add_demo_data(admin_id):
    """Keep every existing row; repeated clicks do not duplicate examples."""
    members = [
        ('DEMO-RAHUL', 'Rahul Kumar (demo)', 'active'),
        ('DEMO-ARUN', 'Arun S (demo)', 'expired'),
        ('DEMO-PRIYA', 'Priya M (demo)', 'active'),
        ('DEMO-DEEPAK', 'Deepak R (demo)', 'active'),
        ('DEMO-MEERA', 'Meera V (demo)', 'active'),
        ('DEMO-KARTHIK', 'Karthik N (demo)', 'pending'),
    ]
    created = 0
    examples = 0
    conn = get_connection()
    try:
        # One transaction makes retry safe, including two simultaneous clicks.
        conn.execute('BEGIN IMMEDIATE')
        for user_id, name, payment in members:
            exists = conn.execute('SELECT is_demo FROM users WHERE user_id=?', (user_id,)).fetchone()
            if exists is None:
                conn.execute('''INSERT INTO users
                    (user_id,name,payment_status,department,year,active,is_demo,face_enrollment_source)
                    VALUES (?,?,?,'Demo profile',3,1,1,'none')''', (user_id, name, payment))
                created += 1
            elif not exists['is_demo']:
                continue  # A real/enrolled profile must never be overwritten.
            reason = ('DEMO EXAMPLE — eligible member would be permitted after real identity verification'
                      if payment == 'active' else f'DEMO EXAMPLE — payment {payment} blocks entry')
            if not conn.execute("SELECT 1 FROM entry_logs WHERE event_source='sample' AND recognized_id=? AND reason=?", (user_id, reason)).fetchone():
                conn.execute('''INSERT INTO entry_logs
                    (recognized_id,decision,reason,tag,payment_status,event_source,comparison_performed)
                    VALUES (?,?,?,?,?,'sample',0)''',
                    (user_id, 'GRANTED' if payment == 'active' else 'DENIED', reason,
                     'authorized' if payment == 'active' else 'unpaid', payment))
                examples += 1
        if created or examples:
            conn.execute('INSERT INTO admin_actions(admin_id,action,reason) VALUES (?,?,?)',
                         (admin_id, 'Add labelled demo examples', f'{created} profiles; {examples} sample decisions; no biometrics or notifications'))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return {'members_created': created, 'examples_created': examples,
            'message': 'Demo examples added. No faces enrolled, attendance marked or Telegram messages sent.'}
