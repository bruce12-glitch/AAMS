#!/usr/bin/env python3
"""
Backup database script.
Run: python -m scripts.backup_db
"""

import sys
import sqlite3
from datetime import datetime
sys.path.insert(0, '..')

from app.config import get_database_path

def main():
    db_path = get_database_path()
    backup_path = f"{db_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    try:
        with sqlite3.connect(str(db_path)) as source, sqlite3.connect(backup_path) as target:
            source.backup(target)
        print(f"[OK] Database backed up to: {backup_path}")
    except Exception as e:
        print(f"[FAIL] Backup failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()

