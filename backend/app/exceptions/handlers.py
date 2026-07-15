from fastapi import Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.logging import logger
from app.exceptions.base import AppException
from app.responses.envelope import build_error_response
from app.responses.errors import ErrorCode


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handles custom application domain exceptions and formats standard response envelopes."""
    envelope = build_error_response(code=exc.error_code, message=exc.message, details=exc.details)

    # Internal logging depending on error severity
    if exc.status_code >= 500:
        logger.error(f"AppException {exc.error_code}: {exc.message}", exc_info=exc)
    else:
        logger.warning(f"AppException {exc.error_code}: {exc.message} | Details: {exc.details}")

    return JSONResponse(status_code=exc.status_code, content=jsonable_encoder(envelope))


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Catches and normalizes raw FastAPI/Pydantic validation errors, preventing raw schemas leaks."""
    errors_list = []
    for err in exc.errors():
        # Build readable parameter location paths
        field_path = " -> ".join(str(loc) for loc in err.get("loc", []))
        errors_list.append({"field": field_path, "message": err.get("msg", ""), "type": err.get("type", "")})

    envelope = build_error_response(
        code=ErrorCode.VALIDATION_ERROR, message="Request validation failed.", details=errors_list
    )

    logger.warning(f"Validation failure for request: {errors_list}")

    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=jsonable_encoder(envelope))


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler for unhandled Python system exceptions, keeping tracebacks strictly internal."""
    envelope = build_error_response(
        code=ErrorCode.INTERNAL_SERVER_ERROR, message="An unexpected system error occurred."
    )

    logger.error(f"Unhandled system exception: {str(exc)}", exc_info=exc)

    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=jsonable_encoder(envelope))


from starlette.exceptions import HTTPException


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Normalizes default FastAPI HTTPExceptions into standardized envelope response formats."""
    code = ErrorCode.BAD_REQUEST
    if exc.status_code == 404:
        code = ErrorCode.NOT_FOUND
    elif exc.status_code == 401:
        code = ErrorCode.AUTH_UNAUTHORIZED
    elif exc.status_code == 403:
        code = ErrorCode.FORBIDDEN
    elif exc.status_code == 429:
        code = ErrorCode.RATE_LIMIT_EXCEEDED

    envelope = build_error_response(
        code=code, message=str(exc.detail) if hasattr(exc, "detail") else "HTTP Exception occurred."
    )
    return JSONResponse(status_code=exc.status_code, content=jsonable_encoder(envelope))
