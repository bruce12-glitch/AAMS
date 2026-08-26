"""
Rate limiting for FacePass FabLab.

Backends:
  - MemoryBackend (default): in-process fixed window, zero dependencies.
  - RedisBackend (opt-in via REDIS_URL env): shared window across replicas
    using atomic INCR + EXPIRE; falls back to memory on any Redis error.

Configure via env:
    RATE_LIMIT_PER_MIN (default 120)
    REDIS_URL          (e.g. redis://localhost:6379/0)
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


class MemoryBackend:
    """Per-process fixed-window counter."""

    def __init__(self):
        self._hits = defaultdict(deque)

    def allow(self, key: str, limit: int, window: int) -> bool:
        now = time.monotonic()
        bucket = self._hits[key]
        cutoff = now - window
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()
        if len(bucket) >= limit:
            return False
        bucket.append(now)
        if len(self._hits) > 10_000:  # opportunistic idle-IP cleanup
            stale = [k for k, v in self._hits.items() if not v or v[-1] <= cutoff]
            for k in stale:
                del self._hits[k]
        return True

    def retry_after(self, key: str, window: int) -> int:
        bucket = self._hits.get(key)
        if not bucket:
            return 1
        return max(1, int(window - (time.monotonic() - bucket[0])) + 1)


class RedisBackend:
    """Shared fixed-window counter (INCR/EXPIRE). Fail-open to memory."""

    def __init__(self, url: str):
        import redis  # optional dependency: pip install redis
        self._client = redis.Redis.from_url(
            url, socket_connect_timeout=1, socket_timeout=1, decode_responses=True)
        self._memory = MemoryBackend()

    def allow(self, key: str, limit: int, window: int) -> bool:
        try:
            full = f'rl:{key}'
            count = self._client.incr(full)
            if count == 1:
                self._client.expire(full, window)
            return count <= limit
        except Exception:
            return self._memory.allow(key, limit, window)

    def retry_after(self, key: str, window: int) -> int:
        try:
            ttl = self._client.ttl(f'rl:{key}')
            return max(1, int(ttl)) if ttl and ttl > 0 else 1
        except Exception:
            return self._memory.retry_after(key, window)


_backend = None


def get_backend():
    global _backend
    if _backend is None:
        url = os.getenv('REDIS_URL', '')
        if url:
            try:
                _backend = RedisBackend(url)
            except Exception:
                _backend = MemoryBackend()
        else:
            _backend = MemoryBackend()
    return _backend


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Fixed-window per-IP request limiter with pluggable backend."""

    def __init__(self, app, limit: int = None, window_seconds: int = 60):
        super().__init__(app)
        self.limit = limit if limit is not None else requests_per_minute()
        self.window = window_seconds
        self.backend = get_backend()

    @staticmethod
    def _client_ip(request: Request) -> str:
        # Trust the socket peer; a reverse proxy should handle X-Forwarded-For.
        return request.client.host if request.client else 'unknown'

    async def dispatch(self, request: Request, call_next):
        if request.url.path in EXEMPT_PATHS:
            return await call_next(request)

        ip = self._client_ip(request)
        if not self.backend.allow(ip, self.limit, self.window):
            retry_after = self.backend.retry_after(ip, self.window)
            return JSONResponse(
                {'detail': f'Rate limit exceeded ({self.limit} req/min)'},
                status_code=429,
                headers={'Retry-After': str(retry_after)},
            )

        return await call_next(request)
