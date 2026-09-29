"""
Shared test fixtures.

The API applies a fixed-window rate limiter (per IP, and per mail ID for
sign-in). Counters live in one process-wide singleton, so without a reset
every Nth test in the suite would fail with 429 instead of testing what it
actually cares about.
"""

import pytest


@pytest.fixture(autouse=True)
def _fresh_rate_limits():
    from app.ratelimit import reset_rate_limits

    reset_rate_limits()
    yield
    reset_rate_limits()
