"""Capture provenance for operational views; old data is preserved, not guessed."""
from typing import Literal

RecordScope = Literal['recorded', 'history', 'all']
RECORDED = "('snapshot','webcam','door_camera','system')"
SECURITY_ALERTS = "alert_type NOT IN ('ANNOUNCE','REPORT','ENROLLMENT','ENTRY','TEST')"


def scope_sql(scope, column='event_source'):
    if scope == 'recorded':
        return f'{column} IN {RECORDED}'
    if scope == 'history':
        return f"{column} NOT IN {RECORDED}"
    return '1=1'


def source_counts(conn, table, condition='1=1'):
    if table not in ('entry_logs', 'alerts'):
        raise ValueError('Unsupported event table')
    rows = conn.execute(f'SELECT event_source, COUNT(*) AS count FROM {table} WHERE {condition} GROUP BY event_source').fetchall()
    return {row['event_source']: row['count'] for row in rows}
