"""
Database connection and ORM helpers for FacePass FabLab.
Implements §16 Database Schema with 6 tables.
"""

import sqlite3
from pathlib import Path
from app.config import get_database_path

# Database path
DATABASE_PATH = get_database_path()

def get_connection():
    """
    Get a SQLite database connection.
    Returns a connection object with row_factory set for dict-like access.
    """
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """
    Initialize the database by creating all tables if they don't exist.
    This is called by scripts/create_db.py
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Table 1: users (§16.1)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            phone TEXT,
            email TEXT,
            user_type TEXT DEFAULT 'student',
            payment_status TEXT DEFAULT 'inactive',
            payment_expiry TEXT,
            face_embedding BLOB,
            face_embedding_2 BLOB,
            face_embedding_3 BLOB,
            face_image_path TEXT,
            consent_given INTEGER DEFAULT 0,
            active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Table 2: tokens (§16.2)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token_value TEXT UNIQUE NOT NULL,
            user_id TEXT NOT NULL,
            token_type TEXT DEFAULT 'qr',
            active INTEGER DEFAULT 1,
            issued_at TEXT DEFAULT CURRENT_TIMESTAMP,
            expires_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    ''')
    
    # Table 3: entry_logs (§16.3)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS entry_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_time TEXT DEFAULT CURRENT_TIMESTAMP,
            claimed_id TEXT,
            recognized_id TEXT,
            similarity REAL,
            payment_status TEXT,
            liveness_status TEXT,
            decision TEXT,
            reason TEXT,
            tag TEXT,
            image_path TEXT,
            location TEXT DEFAULT 'fab_lab_entrance'
        )
    ''')
    
    # Table 4: occupants (§16.4)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS occupants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            entry_time TEXT NOT NULL,
            last_seen_time TEXT,
            exit_time TEXT,
            status TEXT DEFAULT 'inside',
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    ''')
    
    # Table 5: alerts (§16.5)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alert_type TEXT NOT NULL,
            severity TEXT DEFAULT 'medium',
            message TEXT NOT NULL,
            image_path TEXT,
            approved INTEGER DEFAULT 0,
            approved_at TEXT,
            acked INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            sent_at TEXT,
            sent_status TEXT DEFAULT 'pending'
        )
    ''')
    
    # Table 6: admin_actions (§16.6)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id TEXT DEFAULT 'Dr. Meena K.',
            action TEXT NOT NULL,
            target_user_id TEXT,
            reason TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def dict_from_row(row):
    """Convert a sqlite3.Row to a dictionary."""
    if row is None:
        return None
    return dict(zip(row.keys(), row))

def list_from_rows(rows):
    """Convert a list of sqlite3.Row objects to a list of dictionaries."""
    return [dict_from_row(row) for row in rows]
