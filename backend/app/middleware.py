from __future__ import annotations

import logging
import re
import time
from collections import defaultdict
from typing import Callable
from uuid import uuid4

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger("mishkat.access")

# Scrub sensitive patterns (tokens, passwords, secrets, emails, keys)
SENSITIVE_PATTERNS = [
    (re.compile(r'(?i)(password|secret|token|api[_-]?key)["\']?\s*[:=]\s*["\']?([^"\'\s&]+)'), r'\1="[REDACTED]"'),
    (re.compile(r'Bearer\s+[A-Za-z0-9\-_.]+', re.IGNORECASE), 'Bearer [REDACTED]'),
]


def redact_sensitive_text(text: str) -> str:
    redacted = text
    for pattern, repl in SENSITIVE_PATTERNS:
        redacted = pattern.sub(repl, redacted)
    return redacted


class RateLimiter:
    """In-memory sliding window rate limiter per client IP."""

    def __init__(self, requests_per_minute: int = 120):
        self.rpm = requests_per_minute
        self.window = 60.0
        self._requests: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, client_id: str) -> bool:
        now = time.time()
        cutoff = now - self.window
        timestamps = self._requests[client_id]
        # Purge timestamps older than window
        self._requests[client_id] = [t for t in timestamps if t > cutoff]
        if len(self._requests[client_id]) >= self.rpm:
            return False
        self._requests[client_id].append(now)
        return True


rate_limiter = RateLimiter(requests_per_minute=200)


class SecurityAndObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Extract or generate safe request ID
        supplied_id = request.headers.get("x-request-id", "")
        request_id = (
            supplied_id[:80]
            if supplied_id and all(ch.isalnum() or ch in "-_." for ch in supplied_id)
            else str(uuid4())
        )
        request.state.request_id = request_id

        # Rate limit checks on API routes
        client_ip = request.client.host if request.client else "unknown"
        if request.url.path.startswith("/api/"):
            if not rate_limiter.is_allowed(client_ip):
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "Rate limit exceeded. Please throttle your requests.",
                        "request_id": request_id,
                    },
                    headers={"X-Request-ID": request_id, "Retry-After": "60"},
                )

        try:
            response = await call_next(request)
        except Exception as exc:
            # Structured error response without leaking tracebacks
            error_type = type(exc).__name__
            logger.error(
                "Unhandled error in request_id=%s path=%s: %s",
                request_id,
                request.url.path,
                redact_sensitive_text(str(exc)),
            )
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal Server Error",
                    "code": error_type,
                    "request_id": request_id,
                    "message": "An unexpected server error occurred. Inspect server logs using request_id.",
                },
                headers={"X-Request-ID": request_id},
            )

        # Conservative browser/API security headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"

        if request.url.path.startswith("/api/") or request.url.path == "/api":
            response.headers["Cache-Control"] = "no-store, max-age=0"
            response.headers["Pragma"] = "no-cache"

        from .settings import settings
        if settings.environment.lower() == "production":
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
                "font-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'self'; "
                "frame-ancestors 'none'; form-action 'self'"
            )
            if request.url.scheme == "https":
                response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response
