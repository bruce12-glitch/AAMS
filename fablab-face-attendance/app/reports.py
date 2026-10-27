"""
Reports Engine for FacePass FabLab.
Generates daily, weekly, proxy, unpaid, and occupancy reports per §15.2.
"""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from app.database import get_connection

class ReportGenerator:
    """
    Generates various reports for dashboard and Telegram notifications.
    """
    
    def __init__(self):
        """Initialize report generator."""
        pass
    
    def generate_daily(self, date_str: str = None) -> dict:
        """
        Generate daily report in exact format from §15.2 #7.
        
        Returns:
            {
                "title": "Fab Lab Daily Report",
                "date": "22 Aug 2026",
                "total_entries": 42,
                "unique_users": 28,
                "authorized": 39,
                "proxy_attempts": 1,
                "unpaid_attempts": 2,
                "unknown_attempts": 0,
                "spoof_attempts": 0,
                "active_users": [
                    {"name": "Rahul Kumar", "entry": "10:32 AM", "exit": "1:15 PM"},
                    ...
                ]
            }
        """
        if date_str is None:
            date_str = datetime.now(ZoneInfo('Asia/Kolkata')).strftime('%Y-%m-%d')
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get date range
        start_dt = datetime.strptime(date_str, '%Y-%m-%d')
        end_dt = start_dt + timedelta(days=1)
        start_ts = start_dt.replace(tzinfo=ZoneInfo('Asia/Kolkata')).astimezone(timezone.utc).isoformat()
        end_ts = end_dt.replace(tzinfo=ZoneInfo('Asia/Kolkata')).astimezone(timezone.utc).isoformat()
        
        # Total entries
        cursor.execute('''
            SELECT COUNT(*) as count FROM entry_logs 
            WHERE event_source<>'sample' AND decision='GRANTED' AND datetime(event_time) >= datetime(?) AND datetime(event_time) < datetime(?)
        ''', (start_ts, end_ts))
        total_entries = cursor.fetchone()['count']
        
        # Unique users
        cursor.execute('''
            SELECT COUNT(DISTINCT recognized_id) as count FROM entry_logs 
            WHERE event_source<>'sample' AND decision='GRANTED' AND datetime(event_time) >= datetime(?) AND datetime(event_time) < datetime(?) AND recognized_id IS NOT NULL
        ''', (start_ts, end_ts))
        unique_users = cursor.fetchone()['count']
        
        # Count by tag
        cursor.execute('''
            SELECT tag, COUNT(*) as count FROM entry_logs 
            WHERE event_source<>'sample' AND datetime(event_time) >= datetime(?) AND datetime(event_time) < datetime(?)
            GROUP BY tag
        ''', (start_ts, end_ts))
        
        tag_counts = {}
        for row in cursor.fetchall():
            tag_counts[row['tag']] = row['count']
        
        authorized = tag_counts.get('authorized', 0)
        proxy_attempts = tag_counts.get('proxy', 0)
        unpaid_attempts = tag_counts.get('unpaid', 0)
        unknown_attempts = tag_counts.get('unknown', 0)
        spoof_attempts = tag_counts.get('spoof', 0)
        
        # Active users (entered and exited today)
        cursor.execute('''
            SELECT u.name, o.entry_time, o.exit_time
            FROM occupants o
            JOIN users u ON o.user_id = u.user_id
            WHERE datetime(o.entry_time) >= datetime(?) AND datetime(o.entry_time) < datetime(?)
            AND o.exit_time IS NOT NULL
            ORDER BY o.entry_time
        ''', (start_ts, end_ts))
        
        active_users = []
        for row in cursor.fetchall():
            entry_dt = datetime.fromisoformat(row['entry_time']).replace(tzinfo=timezone.utc).astimezone(ZoneInfo('Asia/Kolkata'))
            exit_dt = datetime.fromisoformat(row['exit_time']).replace(tzinfo=timezone.utc).astimezone(ZoneInfo('Asia/Kolkata'))
            
            active_users.append({
                'name': row['name'],
                'entry': entry_dt.strftime('%I:%M %p'),
                'exit': exit_dt.strftime('%I:%M %p')
            })
        
        conn.close()
        
        return {
            'title': 'Fab Lab Daily Report',
            'date': start_dt.strftime('%d %b %Y'),
            'total_entries': total_entries,
            'unique_users': unique_users,
            'authorized': authorized,
            'proxy_attempts': proxy_attempts,
            'unpaid_attempts': unpaid_attempts,
            'unknown_attempts': unknown_attempts,
            'spoof_attempts': spoof_attempts,
            'active_users': active_users
        }
    
    def generate_weekly(self) -> dict:
        """Generate weekly summary report."""
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get last 7 days
        end_dt = datetime.now(timezone.utc)
        start_dt = end_dt - timedelta(days=7)
        
        cursor.execute('''
            SELECT DATE(event_time, '+330 minutes') as date, COUNT(*) as entries,
                   COUNT(DISTINCT recognized_id) as unique_users
            FROM entry_logs
            WHERE event_source<>'sample' AND decision='GRANTED' AND datetime(event_time) >= datetime(?)
            GROUP BY DATE(event_time, '+330 minutes')
            ORDER BY date DESC
        ''', (start_dt.isoformat(),))
        
        daily_stats = []
        for row in cursor.fetchall():
            daily_stats.append({
                'date': row['date'],
                'entries': row['entries'],
                'unique_users': row['unique_users']
            })
        
        conn.close()
        
        return {
            'title': 'Fab Lab Weekly Report',
            'period': f"{start_dt.strftime('%d %b')} - {end_dt.strftime('%d %b %Y')}",
            'daily_stats': daily_stats
        }
    
    def generate_proxy_report(self) -> dict:
        """Generate proxy attempt report."""
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT el.*, u.name as claimed_name
            FROM entry_logs el
            LEFT JOIN users u ON el.claimed_id = u.user_id
            WHERE el.tag = 'proxy' AND el.event_source<>'sample'
            ORDER BY el.event_time DESC
            LIMIT 50
        ''')
        
        attempts = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return {
            'title': 'Proxy Attempt Report',
            'total_attempts': len(attempts),
            'attempts': attempts
        }
    
    def generate_unpaid_report(self) -> dict:
        """Generate unpaid attempt report."""
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT el.*, u.name
            FROM entry_logs el
            LEFT JOIN users u ON el.recognized_id = u.user_id
            WHERE el.tag = 'unpaid' AND el.event_source<>'sample'
            ORDER BY el.event_time DESC
            LIMIT 50
        ''')
        
        attempts = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return {
            'title': 'Unpaid Entry Attempt Report',
            'total_attempts': len(attempts),
            'attempts': attempts
        }
    
    def generate_occupancy_report(self) -> dict:
        """Generate occupancy statistics report."""
        conn = get_connection()
        cursor = conn.cursor()
        
        # Current occupants
        cursor.execute('''
            SELECT COUNT(*) as count FROM occupants WHERE status = 'inside'
        ''')
        current_count = cursor.fetchone()['count']
        
        # Peak simultaneous occupancy and time-weighted daily average.
        from app.utils import utc_now, parse_timestamp
        now = utc_now()
        day = datetime.now(ZoneInfo('Asia/Kolkata')).replace(hour=0, minute=0, second=0, microsecond=0)
        start = day.astimezone(timezone.utc).replace(tzinfo=None)
        rows = cursor.execute("SELECT entry_time, exit_time FROM occupants WHERE datetime(entry_time)<=datetime(?) AND (exit_time IS NULL OR datetime(exit_time)>=datetime(?))", (now.isoformat(), start.isoformat())).fetchall()
        events = []
        person_seconds = 0.0
        for row in rows:
            begin = max(start, parse_timestamp(row['entry_time']))
            finish = min(now, parse_timestamp(row['exit_time']) if row['exit_time'] else now)
            if finish > begin:
                events.extend([(begin, 1), (finish, -1)])
                person_seconds += (finish - begin).total_seconds()
        peak_occupancy = 0
        present = 0
        for _stamp, change in sorted(events):
            present += change
            peak_occupancy = max(peak_occupancy, present)
        avg_occupancy = person_seconds / max(1.0, (now - start).total_seconds())

        conn.close()
        
        return {
            'title': 'Occupancy Report',
            'current_occupants': current_count,
            'peak_today': peak_occupancy,
            'average_today': round(avg_occupancy, 1)
        }
    
    def to_plain_text(self, report: dict) -> str:
        """
        Convert report dictionary to plain text for Telegram/clipboard.
        """
        lines = [report.get('title', 'Report')]
        lines.append('=' * 40)
        
        for key, value in report.items():
            if key == 'title':
                continue
            if isinstance(value, list):
                lines.append(f"{key.replace('_', ' ').title()}: {len(value)}")
                for item in value[:5]:  # Show first 5 items
                    if isinstance(item, dict):
                        lines.append(f"  - {item.get('name', 'Unknown')}")
            elif isinstance(value, (int, float)):
                lines.append(f"{key.replace('_', ' ').title()}: {value}")
            else:
                lines.append(f"{key.replace('_', ' ').title()}: {value}")
        
        return '\n'.join(lines)
