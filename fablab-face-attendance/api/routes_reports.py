"""
Reports API Routes for FacePass FabLab.
Implements GET daily/weekly/proxy/unpaid/occupancy reports.
"""

from fastapi import APIRouter

router = APIRouter(prefix='/api/reports', tags=['reports'])

@router.get('/daily')
async def get_daily_report():
    """Get daily report data."""
    from app.reports import ReportGenerator
    
    gen = ReportGenerator()
    return gen.generate_daily()

@router.get('/weekly')
async def get_weekly_report():
    """Get weekly report data."""
    from app.reports import ReportGenerator
    
    gen = ReportGenerator()
    return gen.generate_weekly()

@router.get('/proxy')
async def get_proxy_report():
    """Get proxy attempt report."""
    from app.reports import ReportGenerator
    
    gen = ReportGenerator()
    return gen.generate_proxy_report()

@router.get('/unpaid')
async def get_unpaid_report():
    """Get unpaid attempt report."""
    from app.reports import ReportGenerator
    
    gen = ReportGenerator()
    return gen.generate_unpaid_report()

@router.get('/occupancy')
async def get_occupancy_report():
    """Get occupancy report."""
    from app.reports import ReportGenerator
    
    gen = ReportGenerator()
    return gen.generate_occupancy_report()
