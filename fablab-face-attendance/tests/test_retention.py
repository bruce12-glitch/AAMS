"""
Tests for the §26.4 retention policy enforcement.
Uses a temporary database so the developer's real data is untouched.
"""

import sqlite3
from datetime import datetime, timedelta

import pytest

import app.database as dbmod
import app.retention as retention


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Point app.database at a throwaway DB and initialize schema."""
    db_file = tmp_path / 'retention_test.db'
    monkeypatch.setattr(dbmod, 'DATABASE_PATH', str(db_file))

    from app.database import init_db
    init_db()
    return db_file


def _insert_log(event_time):
    conn = sqlite3.connect(dbmod.DATABASE_PATH)
    conn.execute(
        'INSERT INTO entry_logs (event_time, decision, reason, tag) VALUES (?, ?, ?, ?)',
        (event_time, 'DENIED', 'test', 'unknown'),
    )
    conn.commit()
    conn.close()


def test_old_entry_logs_purged_new_kept(temp_db):
    old = (datetime.now() - timedelta(days=120)).strftime('%Y-%m-%d %H:%M:%S')
    recent = (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d %H:%M:%S')
    _insert_log(old)
    _insert_log(recent)

    removed = retention.purge_entry_logs(90)

    assert removed == 1
    conn = sqlite3.connect(dbmod.DATABASE_PATH)
    remaining = conn.execute('SELECT COUNT(*) FROM entry_logs').fetchone()[0]
    conn.close()
    assert remaining == 1


def test_alert_images_deleted_and_nulled(temp_db, tmp_path):
    import os

    old_date = (datetime.now() - timedelta(days=45)).isoformat(sep=' ')
    img_dir = tmp_path / 'alerts'
    img_dir.mkdir()
    img_file = img_dir / 'old.jpg'
    img_file.write_bytes(b'\xff\xd8fakejpeg')

    conn = sqlite3.connect(dbmod.DATABASE_PATH)
    conn.execute(
        'INSERT INTO alerts (alert_type, message, image_path, created_at) VALUES (?, ?, ?, ?)',
        ('UNKNOWN', 'test', str(img_file), old_date),
    )
    conn.execute(
        'INSERT INTO alerts (alert_type, message, image_path, created_at) VALUES (?, ?, ?, ?)',
        ('UNKNOWN', 'recent', None, datetime.now().isoformat(sep=' ')),
    )
    conn.commit()
    conn.close()

    removed = retention.purge_alert_images(30, images_root=tmp_path)

    assert removed == 1
    assert not os.path.exists(img_file)

    conn = sqlite3.connect(dbmod.DATABASE_PATH)
    stale_path = conn.execute(
        "SELECT image_path FROM alerts WHERE message = 'test'"
    ).fetchone()[0]
    total = conn.execute('SELECT COUNT(*) FROM alerts').fetchone()[0]
    conn.close()
    assert stale_path is None   # stale reference cleared
    assert total == 2           # metadata rows retained for audit trail


def test_apply_retention_summary(temp_db):
    summary = retention.apply_retention()
    assert set(summary) == {'entry_logs_purged', 'alert_images_removed'}
