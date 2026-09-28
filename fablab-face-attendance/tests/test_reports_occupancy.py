"""Regression: occupancy report must not 500 (was GROUP BY HOUR(), not SQLite)."""

from app.reports import ReportGenerator


def test_occupancy_report_runs():
    report = ReportGenerator().generate_occupancy_report()
    assert report['title'] == 'Occupancy Report'
    assert isinstance(report['current_occupants'], int)
    assert isinstance(report['peak_today'], int)
    assert isinstance(report['average_today'], (int, float))
