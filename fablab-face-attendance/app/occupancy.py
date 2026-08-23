"""
Occupancy Tracking for FacePass FabLab.
Implements §14 Occupancy Management with timeout logic.
"""

from datetime import datetime, timedelta
from app.database import get_connection
from app.config import get_occupancy_config

class OccupancyTracker:
    """
    Tracks occupants inside the Fab Lab with entry/exit times and timeout logic.
    """
    
    def __init__(self):
        """Initialize occupancy tracker with configuration."""
        config = get_occupancy_config()
        self.timeout_minutes = config.get('timeout_minutes', 30)
        self.indoor_scan_enabled = config.get('indoor_scan_enabled', False)
        self.scan_interval = config.get('indoor_scan_interval_seconds', 120)
    
    def mark_inside(self, user_id: str) -> dict:
        """
        Mark a user as entered the Fab Lab.
        
        Args:
            user_id: The user's unique ID
            
        Returns:
            Dictionary with success status and occupant info
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check if user is already marked as inside
        cursor.execute('''
            SELECT id, entry_time, status FROM occupants 
            WHERE user_id = ? AND status = 'inside'
        ''', (user_id,))
        
        existing = cursor.fetchone()
        
        if existing:
            conn.close()
            return {
                'success': False,
                'reason': 'User already marked as inside',
                'occupant_id': existing['id']
            }
        
        # Create new occupancy record
        entry_time = datetime.now().isoformat()
        
        cursor.execute('''
            INSERT INTO occupants (user_id, entry_time, last_seen_time, status)
            VALUES (?, ?, ?, 'inside')
        ''', (user_id, entry_time, entry_time))
        
        conn.commit()
        occupant_id = cursor.lastrowid
        
        conn.close()
        
        return {
            'success': True,
            'occupant_id': occupant_id,
            'entry_time': entry_time
        }
    
    def mark_exit(self, user_id: str) -> dict:
        """
        Mark a user as exited the Fab Lab.
        
        Args:
            user_id: The user's unique ID
            
        Returns:
            Dictionary with success status and exit info
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        exit_time = datetime.now().isoformat()
        
        # Update the active occupancy record
        cursor.execute('''
            UPDATE occupants 
            SET exit_time = ?, status = 'exited', last_seen_time = ?
            WHERE user_id = ? AND status = 'inside'
        ''', (exit_time, exit_time, user_id))
        
        rows_affected = cursor.rowcount
        conn.commit()
        conn.close()
        
        if rows_affected == 0:
            return {
                'success': False,
                'reason': 'No active occupancy record found for user'
            }
        
        return {
            'success': True,
            'exit_time': exit_time
        }
    
    def mark_timeout(self, user_id: str) -> dict:
        """
        Mark a user as timed out (exceeded maximum stay duration).
        
        Args:
            user_id: The user's unique ID
            
        Returns:
            Dictionary with success status
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        exit_time = datetime.now().isoformat()
        
        cursor.execute('''
            UPDATE occupants 
            SET exit_time = ?, status = 'timeout_exited', last_seen_time = ?
            WHERE user_id = ? AND status = 'inside'
        ''', (exit_time, exit_time, user_id))
        
        rows_affected = cursor.rowcount
        conn.commit()
        conn.close()
        
        return {
            'success': rows_affected > 0,
            'exit_time': exit_time if rows_affected > 0 else None
        }
    
    def check_timeouts(self) -> list:
        """
        Check all current occupants for timeout violations.
        Users who have been inside longer than timeout_minutes are marked as timeout_exited.
        
        Returns:
            List of users who were timed out
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get all users currently inside
        cursor.execute('''
            SELECT user_id, entry_time FROM occupants WHERE status = 'inside'
        ''')
        
        inside_users = cursor.fetchall()
        conn.close()
        
        timeout_users = []
        now = datetime.now()
        timeout_delta = timedelta(minutes=self.timeout_minutes)
        
        for row in inside_users:
            try:
                entry_time = datetime.fromisoformat(row['entry_time'])
                
                if now - entry_time > timeout_delta:
                    # User has exceeded timeout
                    result = self.mark_timeout(row['user_id'])
                    if result['success']:
                        timeout_users.append({
                            'user_id': row['user_id'],
                            'entry_time': row['entry_time'],
                            'timeout_time': now.isoformat()
                        })
            except (ValueError, TypeError):
                # Invalid date format, skip
                continue
        
        return timeout_users
    
    def get_current_occupants(self) -> list:
        """
        Get all users currently inside the Fab Lab.
        
        Returns:
            List of occupant dictionaries with user info
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT o.id, o.user_id, o.entry_time, o.last_seen_time, 
                   u.name, u.user_type
            FROM occupants o
            LEFT JOIN users u ON o.user_id = u.user_id
            WHERE o.status = 'inside'
            ORDER BY o.entry_time ASC
        ''')
        
        occupants = []
        for row in cursor.fetchall():
            occupants.append(dict(row))
        
        conn.close()
        return occupants
    
    def get_occupancy_count(self) -> int:
        """Get the current number of people inside."""
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) as count FROM occupants WHERE status = \'inside\'')
        result = cursor.fetchone()
        count = result['count'] if result else 0
        
        conn.close()
        return count
    
    def update_last_seen(self, user_id: str) -> bool:
        """
        Update the last_seen_time for a user currently inside.
        Used for periodic indoor scanning.
        
        Args:
            user_id: The user's unique ID
            
        Returns:
            True if updated successfully
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        last_seen = datetime.now().isoformat()
        
        cursor.execute('''
            UPDATE occupants 
            SET last_seen_time = ?
            WHERE user_id = ? AND status = 'inside'
        ''', (last_seen, user_id))
        
        rows_affected = cursor.rowcount
        conn.commit()
        conn.close()
        
        return rows_affected > 0
