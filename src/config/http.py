from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette import status


limiter = Limiter(key_func=get_remote_address)


def too_many_request(request: Request, exc: RateLimitExceeded):
    return JSONResponse(status_code=429, content={"detail": "too many requests."})


def unexpected(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "something went wrong."},
    )
