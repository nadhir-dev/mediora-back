from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette import status
from starlette.middleware.base import BaseHTTPMiddleware


limiter = Limiter(key_func=get_remote_address)

allowed_origins = [
    "http://localhost",
    "http://localhost:5173",
    "http://localhost:5174",
]


def too_many_request(request: Request, exc: RateLimitExceeded):
    return JSONResponse(status_code=429, content={"detail": "too many requests."})


def unexpected(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "something went wrong."},
    )


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        return response
