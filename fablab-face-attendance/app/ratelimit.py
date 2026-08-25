"""
Lightweight in-memory rate limiter (fixed window, per client IP).

Prototype-grade: per-process state, resets on restart, no distributed
coordination. Sufficient to stop brute-force/token-guessing on a single
lab deployment; swap for slowapi/Redis behind a multi-instance rollout.

Configure via env:
    RATE_LIMIT_PER_MIN (default 120)
"""

import os
import time
from collections import defaultdict, deque

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

# Paths exempt from limiting (orchestrator probes / UI polling bursts)
EXEMPT_PATHS = {'/health', '/model-status'}


def requests_per_minute() -> int:
    try:
        return max(10, int(os.getenv('RATE_LIMIT_PER_MIN', '120')))
    except ValueError:
        return 120


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Fixed-window per-IP request limiter."""

    def __init__(self, app, limit: int = None, window_seconds: int = 60):
        super().__init__(app)
        self.limit = limit if limit is not None else requests_per_minute()
        self.window = window_seconds
        self._hits = defaultdict(deque)

    def _client_ip(self, request: Request) -> str:
        # Trust the socket peer; a reverse proxy should overwrite this via
        # X-Forwarded-For handling at the proxy layer, not in-app.
        return request.client.host if request.client else 'unknown'

    async def dispatch(self, request: Request, call_next):
        if request.url.path in EXEMPT_PATHS:
            return await call_next(request)

        now = time.monotonic()
        ip = self._client_ip(request)
        bucket = self._hits[ip]

        cutoff = now - self.window
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()

        if len(bucket) >= self.limit:
            retry_after = int(self.window - (now - bucket[0])) + 1
            return JSONResponse(
                {'detail': f'Rate limit exceeded ({self.limit} req/min)'},
                status_code=429,
                headers={'Retry-After': str(max(retry_after, 1))},
            )

        bucket.append(now)

        # Opportunistic cleanup so idle IPs don't accumulate forever
        if len(self._hits) > 10_000:
            stale = [k for k, v in self._hits.items() if not v or v[-1] <= cutoff]
            for k in stale:
                del self._hits[k]

        return await call_next(request)
