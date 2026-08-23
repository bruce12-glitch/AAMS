"""
FastAPI entry point for FacePass FabLab.
Wires all API routes and starts the server.
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title='FacePass FabLab API',
    description='Smart Anti-Proxy Facial Access and Attendance System for SRMIST Fab Lab',
    version='1.0.0'
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

# Include routers
from api.routes_entry import router as entry_router
from api.routes_users import router as users_router
from api.routes_alerts import router as alerts_router
from api.routes_occupants import router as occupants_router
from api.routes_reports import router as reports_router
from api.routes_dashboard import router as dashboard_router
from api.routes_admin import router as admin_router

app.include_router(entry_router)
app.include_router(users_router)
app.include_router(alerts_router)
app.include_router(occupants_router)
app.include_router(reports_router)
app.include_router(dashboard_router)
app.include_router(admin_router)

@app.get('/')
async def root():
    """Root endpoint."""
    return {'message': 'FacePass FabLab API', 'version': '1.0.0'}

@app.get('/health')
async def health_check():
    """Health check endpoint."""
    return {'status': 'healthy'}

@app.on_event('startup')
async def startup_event():
    """Initialize services on startup."""
    logger.info('Starting FacePass FabLab API...')
    
    # Initialize database
    from app.database import init_db
    init_db()
    logger.info('Database initialized')
    
    # Initialize scheduler (if enabled)
    try:
        from app.alerts import AlertService
        from app.reports import ReportGenerator
        from app.scheduler import ReportScheduler
        from app.config import get_database_path
        
        alert_service = AlertService()
        report_gen = ReportGenerator()
        scheduler = ReportScheduler(alert_service, report_gen, get_database_path())
        scheduler.start()
        logger.info('Scheduler started')
    except Exception as e:
        logger.warning(f'Scheduler initialization skipped: {e}')

@app.on_event('shutdown')
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info('Shutting down FacePass FabLab API...')

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)
