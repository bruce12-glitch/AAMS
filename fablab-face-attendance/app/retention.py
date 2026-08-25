"""
Data retention enforcement (§26.4 Retention Policy).

    Entry logs        : 90 days
    Alert images      : 30 days (file + DB reference)
    Enrollment data   : kept until user deleted / consent withdrawn
                        (handled by DELETE /api/users/{id})

Runs nightly from the scheduler; safe to call manually.
"""

import logging
from datetime import date, timedelta
from pathlib import Path

from app.config import BASE_DIR
from app.database import get_connection

logger = logging.getLogger(__name__)

ENTRY_LOG_DAYS = 90
ALERT_IMAGE_DAYS = 30


def purge_entry_logs(days: int = ENTRY_LOG_DAYS) -> int:
    """Delete entry_logs older than `days`. Returns rows removed."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM entry_logs WHERE date(event_time) < date('now', ?)",
        (f'-{int(days)} day',),
    )
    removed = cursor.rowcount
    conn.commit()
    conn.close()
    if removed:
        logger.info('Retention: purged %d entry logs older than %dd', removed, days)
    return removed


def purge_alert_images(days: int = ALERT_IMAGE_DAYS,
                       images_root: Path = None) -> int:
    """
    Delete alert evidence files older than `days` and null their paths.
    Alert metadata rows are retained for the audit trail.
    """
    images_root = Path(images_root) if images_root else BASE_DIR / 'images'
    cutoff = date.today() - timedelta(days=days)

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, image_path FROM alerts "
        "WHERE image_path IS NOT NULL AND date(created_at) < ?",
        (cutoff.isoformat(),),
    )
    stale = cursor.fetchall()

    removed_files = 0
    for row in stale:
        path = BASE_DIR / row['image_path'] \
            if not Path(row['image_path']).is_absolute() else Path(row['image_path'])
        try:
            if path.exists():
                path.unlink()
                removed_files += 1
        except OSError as exc:
            logger.warning('Retention: could not delete %s (%s)', path, exc)
        cursor.execute('UPDATE alerts SET image_path = NULL WHERE id = ?', (row['id'],))

    conn.commit()
    conn.close()
    if stale:
        logger.info('Retention: cleared %d alert images older than %dd',
                    len(stale), days)
    return removed_files


def apply_retention(entry_log_days: int = ENTRY_LOG_DAYS,
                    alert_image_days: int = ALERT_IMAGE_DAYS) -> dict:
    """Run every retention rule; returns a summary for logging/tests."""
    return {
        'entry_logs_purged': purge_entry_logs(entry_log_days),
        'alert_images_removed': purge_alert_images(alert_image_days),
    }
