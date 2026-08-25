"""
Scheduler for FacePass FabLab.
Uses APScheduler for daily reports, occupancy timeouts, and DB backups.
"""

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from app.config import get_config

logger = logging.getLogger(__name__)

class ReportScheduler:
    """
    Manages scheduled tasks using APScheduler.
    - Daily report at 20:00
    - Occupancy timeout check every 5 minutes
    - Database backup daily at 23:00
    """
    
    def __init__(self, alert_service, report_generator, db_path=None):
        """
        Initialize scheduler with services.
        
        Args:
            alert_service: AlertService instance for sending reports
            report_generator: ReportGenerator instance
            db_path: Path to database for backups
        """
        self.alert_service = alert_service
        self.report_generator = report_generator
        self.db_path = db_path
        
        self.scheduler = AsyncIOScheduler()
        self._setup_jobs()
    
    def _setup_jobs(self):
        """Set up all scheduled jobs."""
        config = get_config()
        
        # Daily report at 20:00 (8 PM)
        daily_report_time = config.get('alerts', {}).get('daily_report_time', '20:00')
        hour, minute = map(int, daily_report_time.split(':'))
        
        self.scheduler.add_job(
            self.send_daily_report,
            CronTrigger(hour=hour, minute=minute),
            id='daily_report',
            name='Send daily report'
        )
        
        # Occupancy timeout check every 5 minutes
        self.scheduler.add_job(
            self.check_occupancy_timeouts,
            IntervalTrigger(minutes=5),
            id='occupancy_timeout',
            name='Check occupancy timeouts'
        )
        
        # Database backup daily at 23:00
        self.scheduler.add_job(
            self.backup_database,
            CronTrigger(hour=23, minute=0),
            id='db_backup',
            name='Backup database'
        )

        # Retention enforcement (§26.4) nightly at 03:00
        self.scheduler.add_job(
            self.run_retention,
            CronTrigger(hour=3, minute=0),
            id='retention',
            name='Apply data retention policy'
        )
    
    async def send_daily_report(self):
        """Generate and send daily report at 8 PM."""
        try:
            logger.info("Generating daily report...")
            report = self.report_generator.generate_daily()
            report_text = self.report_generator.to_plain_text(report)
            
            if self.alert_service:
                await self.alert_service.send_daily_report(report_text)
                logger.info("Daily report sent successfully")
        except Exception as e:
            logger.error(f"Failed to send daily report: {e}")
    
    def check_occupancy_timeouts(self):
        """Check for occupants who have exceeded their time limit."""
        try:
            from app.occupancy import OccupancyTracker
            
            tracker = OccupancyTracker()
            timed_out_users = tracker.check_timeouts()
            
            if timed_out_users:
                logger.info(f"Timed out {len(timed_out_users)} users")
                for user in timed_out_users:
                    logger.info(f"User {user['user_id']} timed out at {user['timeout_time']}")
        except Exception as e:
            logger.error(f"Failed to check occupancy timeouts: {e}")
    
    def backup_database(self):
        """Create a backup of the database."""
        try:
            import shutil
            from datetime import datetime
            
            if not self.db_path:
                logger.warning("No database path configured for backup")
                return
            
            backup_path = f"{self.db_path}.backup.{datetime.now().strftime('%Y%m%d')}"
            shutil.copy2(self.db_path, backup_path)
            logger.info(f"Database backed up to {backup_path}")
        except Exception as e:
            logger.error(f"Failed to backup database: {e}")
    
    def run_retention(self):
        """Purge expired entry logs and alert images (§26.4)."""
        try:
            from app.retention import apply_retention
            summary = apply_retention()
            logger.info('Retention run: %s', summary)
        except Exception as e:
            logger.error(f'Failed to apply retention policy: {e}')

    def start(self):
        """Start the scheduler."""
        self.scheduler.start()
        logger.info("Scheduler started")
    
    def shutdown(self):
        """Shutdown the scheduler."""
        self.scheduler.shutdown()
        logger.info("Scheduler shutdown")
