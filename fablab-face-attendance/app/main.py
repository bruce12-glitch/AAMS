"""
FastAPI entry point for FacePass FabLab.
Wires all API routes and starts the server.

Security notes (§27):
  - CORS is restricted to ALLOWED_ORIGINS (default: local dev servers)
  - Mutating routes require X-Admin-Token when API_ADMIN_PASSWORD is set
  - The CV engine loads lazily; the API boots even before models download
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.ratelimit import RateLimitMiddleware, requests_per_minute
from app.security import allowed_origins, auth_enabled, session_security_ready, production_mode

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
# Telegram uses token-bearing URLs; HTTP request logging must never expose them.
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('httpx2').setLevel(logging.WARNING)

@asynccontextmanager
async def lifespan(_app):
    await startup_event()
    try:
        yield
    finally:
        await shutdown_event()


app = FastAPI(
    title='FacePass FabLab API',
    description='Smart Anti-Proxy Facial Access and Attendance System for SRMIST Fab Lab',
    lifespan=lifespan,
    version='1.4.0'
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins(),
    allow_credentials=True,
    allow_methods=['GET', 'POST', 'PUT', 'DELETE'],
    allow_headers=['Content-Type', 'Authorization', 'X-Admin-Token'],
)

app.add_middleware(RateLimitMiddleware)

from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


@app.exception_handler(RequestValidationError)
async def safe_validation_errors(_request, exc):
    # Validation errors must not echo bot tokens, passwords or face payloads.
    detail = [{key: error[key] for key in ('loc', 'msg', 'type')} for error in exc.errors()]
    return JSONResponse(status_code=422, content={'detail': detail})



@app.middleware('http')
async def protect_production_entry(request, call_next):
    # Image processing writes evidence, alerts and occupancy; it is not public.
    if production_mode() and request.url.path.startswith('/api/entry/') and request.method != 'OPTIONS':
        from app.security import require_user
        from fastapi import HTTPException
        from fastapi.responses import JSONResponse
        try:
            await require_user(request)
        except HTTPException as exc:
            return JSONResponse(status_code=exc.status_code, content={'detail': exc.detail})
    return await call_next(request)


# Include routers
from api.routes_entry import router as entry_router
from api.routes_users import router as users_router
from api.routes_alerts import router as alerts_router
from api.routes_occupants import router as occupants_router
from api.routes_reports import router as reports_router
from api.routes_dashboard import router as dashboard_router
from api.routes_admin import router as admin_router
from api.routes_auth import router as auth_router
from api.routes_notify import router as notify_router

app.include_router(entry_router)
app.include_router(users_router)
app.include_router(alerts_router)
app.include_router(occupants_router)
app.include_router(reports_router)
app.include_router(dashboard_router)
app.include_router(admin_router)
app.include_router(auth_router)
app.include_router(notify_router)


@app.get('/')
async def root():
    """Root endpoint."""
    return {'message': 'FacePass FabLab API', 'version': app.version}


@app.get('/health')
async def health_check():
    """
    Liveness probe — intentionally CHEAP and side-effect free.
    Never initializes the CV engine (orchestrator-safe).
    Model state is reported separately at /model-status.
    """
    return {'status': 'ok'}


@app.get('/model-status')
async def model_status():
    """CV engine state without triggering initialization/download."""
    from app.vision import engine_state
    from app.security import auth_enabled, session_security_ready
    return {'cv_engine': engine_state()}


@app.get('/ready')
async def readiness_check():
    """Readiness probe for the database, CV state and Telegram wiring."""
    from fastapi import HTTPException

    from app.config import get_telegram_config
    from app.database import get_connection
    from app.vision import engine_state

    try:
        conn = get_connection()
        conn.execute('SELECT 1').fetchone()
        conn.close()
    except Exception as exc:
        logger.error('Readiness database check failed: %s', exc)
        raise HTTPException(status_code=503, detail='database unavailable')

    telegram = get_telegram_config()
    token = str(telegram.get('bot_token') or '')
    chat_id = str(telegram.get('chat_id') or '')
    placeholder_token = (
        not token or 'here' in token.lower()
        or token.lower() in {'skip', 'none', 'null'}
        or token.startswith('YOUR_')
    )
    placeholder_chat = (
        not chat_id or chat_id.lower() in {'skip', 'none', 'null'}
        or chat_id.startswith('YOUR_')
    )
    return {
        'status': 'ready',
        'database': 'ready',
        'cv_engine': engine_state(),
        'telegram': {
            'enabled': bool(telegram.get('enabled', False)),
            'configured': not placeholder_token and not placeholder_chat,
        },
        'security': {
            'admin_password_configured': auth_enabled(),
            'session_secret_configured': session_security_ready(),
        },
    }


async def startup_event():
    """Initialize services on startup."""
    logger.info('Starting FacePass FabLab API...')

    if production_mode():
        from app.auth import access_password_configured, is_srmist_email, verify_access_password
        from app.security import admin_email, admin_password
        from app.config import get_security_config
        qr_secret = str(get_security_config().get('qr_secret_key') or '')
        if (len(qr_secret) < 32 or qr_secret.startswith('CHANGE_')
                or len(admin_password()) < 12
                or not auth_enabled() or not session_security_ready()
                or not access_password_configured() or not is_srmist_email(admin_email())
                or verify_access_password(admin_password())):
            raise RuntimeError('Production requires distinct administrator and member credentials, an SRMIST administrator email, and a secure session secret')

    from app.database import init_db
    init_db()
    logger.info('Database initialized')

    if not auth_enabled():
        logger.warning(
            '*** API_ADMIN_PASSWORD is not set — admin endpoints are OPEN '
            '(dev mode). Set it in .env before any real deployment. ***'
        )
    if not session_security_ready():
        logger.warning(
            '*** SESSION_SECRET_KEY is not set securely. Set a long random '
            'value before exposing this API. ***'
        )

    # CV engine intentionally NOT loaded here — first request triggers it.
    logger.info('CV engine will lazy-load on first image request')

    try:
        from app.alerts import AlertService
        from app.reports import ReportGenerator
        from app.scheduler import ReportScheduler
        from app.config import get_database_path

        alert_service = AlertService()
        report_gen = ReportGenerator()
        scheduler = ReportScheduler(alert_service, report_gen, get_database_path())
        scheduler.start()
        app.state.report_scheduler = scheduler
        logger.info('Scheduler started')
    except Exception as e:
        logger.warning(f'Scheduler initialization skipped: {e}')

    # Continuous capture is opt-in (config capture.enabled). It owns the
    # process-wide camera handle, so it must start after the scheduler and
    # never be started twice.
    try:
        from app.config import get_config
        if get_config().get('capture', {}).get('enabled', False):
            from app.capture_service import get_capture_service
            get_capture_service().start()
        else:
            logger.info('Capture service disabled (capture.enabled=false)')
    except Exception as e:
        logger.warning(f'Capture service not started: {e}')


async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info('Shutting down FacePass FabLab API...')

    scheduler = getattr(app.state, 'report_scheduler', None)
    if scheduler:
        scheduler.shutdown()

    # Release the camera, or the device stays locked until the process exits.
    try:
        from app.capture_service import get_capture_service
        get_capture_service().stop()
    except Exception as e:
        logger.warning(f'Capture service shutdown skipped: {e}')


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=8000)
