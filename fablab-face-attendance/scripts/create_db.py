#!/usr/bin/env python3
"""
Database creation script for FacePass FabLab.
Creates all 6 tables as specified in §16.
Run: python -m scripts.create_db
"""

import sys
sys.path.insert(0, '..')

from app.database import init_db

def main():
    """Initialize the database with all tables."""
    print("Creating database tables...")
    init_db()
    print("[OK] Database created successfully!")
    print("Tables created:")
    print("  - users")
    print("  - tokens")
    print("  - entry_logs")
    print("  - occupants")
    print("  - alerts")
    print("  - admin_actions")

if __name__ == '__main__':
    main()

