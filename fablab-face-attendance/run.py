#!/usr/bin/env python3
"""
Single command to start the entire FacePass FabLab system.
Usage: python run.py

Steps:
1. Load config.yaml + .env
2. Initialize database (create if not exists)
3. Initialize lightweight services
4. Start FastAPI server on http://localhost:8000
5. Open the API documentation in a browser

The scheduler and remaining services are started by the FastAPI startup event
in app/main.py, which runs inside uvicorn's event loop. They cannot be started
from here — see the note at step 6 in main().
"""

import sys
import os
import logging
import webbrowser
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Start the FacePass FabLab system."""
    logger.info('=' * 50)
    logger.info('Starting FacePass FabLab System')
    logger.info('=' * 50)
    
    # Step 1: Load configuration
    logger.info('Loading configuration...')
    from app.config import get_config
    config = get_config()
    logger.info('Configuration loaded')
    
    # Step 2: Initialize database
    logger.info('Initializing database...')
    from app.database import init_db
    init_db()
    logger.info('Database initialized')
    
    # Step 3: Initialize lightweight services. The heavy InsightFace model is
    # loaded lazily on the first image request so the API can bind immediately
    # and /health remains available while models are downloading.
    logger.info('Initializing LivenessChecker...')
    from app.liveness import LivenessChecker
    liveness_checker = LivenessChecker()
    logger.info('LivenessChecker initialized')
    
    # Step 4: Initialize AlertService
    logger.info('Initializing AlertService...')
    from app.alerts import AlertService
    alert_service = AlertService()
    if alert_service.enabled:
        logger.info('AlertService initialized with Telegram')
    else:
        logger.info('AlertService initialized (Telegram disabled)')
    
    # Step 5: Start FastAPI server.
    #
    # Services (database, alerts, scheduler) are initialised by the FastAPI
    # startup event in app/main.py, which runs INSIDE uvicorn's event loop.
    # They must NOT be started here. AsyncIOScheduler.start() calls
    # asyncio.get_running_loop(), and no loop is running until uvicorn starts
    # one — starting the scheduler here raised
    #     RuntimeError: no running event loop
    # and killed the process before the server ever bound to a port. main.py
    # already does this correctly, and wraps it in try/except so a scheduler
    # fault cannot stop the API from serving.
    logger.info('Starting FastAPI server on http://localhost:8000')
    
    import uvicorn
    from app.main import app
    
    # Run uvicorn in a way that allows other threads
    try:
        # Open browser after a short delay
        def open_browser():
            import time
            time.sleep(2)
            webbrowser.open('http://localhost:8000/docs')
        
        import threading
        browser_thread = threading.Thread(target=open_browser, daemon=True)
        browser_thread.start()
        
        uvicorn.run(app, host='0.0.0.0', port=8000, log_level='info')
    except KeyboardInterrupt:
        logger.info('Shutting down...')
    finally:
        logger.info('FacePass FabLab stopped')

if __name__ == '__main__':
    main()
