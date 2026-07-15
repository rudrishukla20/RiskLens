from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.core.config import settings
from app.responses.envelope import build_error_response
from app.responses.errors import ErrorCode

# Initialize SlowAPI Limiter using the remote client IP address
limiter = Limiter(key_func=get_remote_address, default_limits=[settings.RATE_LIMIT_DEFAULT])

# Reusable rate limit thresholds sourced from settings
LIMIT_DEFAULT = settings.RATE_LIMIT_DEFAULT
LIMIT_LOGIN = settings.RATE_LIMIT_LOGIN
LIMIT_REFRESH = "20/minute"
LIMIT_UPLOAD = settings.RATE_LIMIT_UPLOAD
LIMIT_AI = settings.RATE_LIMIT_AI
LIMIT_REPORT = settings.RATE_LIMIT_REPORT


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """
    Global custom exception handler for SlowAPI RateLimitExceeded exception.
    Ensures 429 errors return the standardized response envelope structure.
    """
    envelope = build_error_response(
        code=ErrorCode.RATE_LIMIT_EXCEEDED,
        message="Rate limit exceeded. Please try again later.",
        details={"info": str(exc.detail) if exc.detail else "Rate limit threshold reached."},
    )
    return JSONResponse(status_code=429, content=jsonable_encoder(envelope))
