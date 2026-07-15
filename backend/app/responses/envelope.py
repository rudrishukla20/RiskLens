import uuid
from datetime import datetime, timezone
from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, Field

from app.core.logging import request_id_ctx
from app.responses.errors import ErrorCode

T = TypeVar("T")


class PaginationMeta(BaseModel):
    """Metadata detailing pagination bounds for array results."""

    page: int = Field(description="Current page number (1-indexed)")
    page_size: int = Field(description="Max items per page limit")
    total_items: int = Field(description="Total count of database records matching parameters")
    total_pages: int = Field(description="Calculated total pages count")
    has_next: bool = Field(description="Flag showing if subsequent pages exist")
    has_previous: bool = Field(description="Flag showing if previous pages exist")


class ResponseMeta(BaseModel):
    """Metadata headers returned with every API response."""

    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    request_id: str = Field(description="Context tracing request identifier")
    pagination: Optional[PaginationMeta] = Field(default=None, description="Active pagination settings")


class ErrorDetails(BaseModel):
    """Details object explaining a transaction failure."""

    code: ErrorCode = Field(description="Standard code string representing category of failure")
    details: Any = Field(description="Contextual warning/failure messages or validation fields errors list")


class ResponseEnvelope(BaseModel, Generic[T]):
    """Standard generic wrapper returned by all API transactions."""

    success: bool = Field(description="Indication of request completion outcome")
    message: str = Field(description="Descriptive outcome message")
    data: Optional[T] = Field(default=None, description="The payload object containing response details")
    error: Optional[ErrorDetails] = Field(default=None, description="Active validation error details")
    meta: ResponseMeta = Field(description="Request execution headers")


def get_current_request_id() -> str:
    """Retrieves request tracing identifier from context, falling back to a fresh UUID."""
    rid = request_id_ctx.get()
    if not rid:
        # Fallback if context is uninitialized (e.g., non-request tasks or testing)
        rid = str(uuid.uuid4())
    return rid


def build_success_response(
    data: Any, message: str = "Request completed successfully.", pagination: Optional[PaginationMeta] = None
) -> ResponseEnvelope[Any]:
    """Helper to cleanly assemble a standardized success response envelope."""
    req_id = get_current_request_id()
    return ResponseEnvelope(
        success=True,
        message=message,
        data=data,
        error=None,
        meta=ResponseMeta(request_id=req_id, pagination=pagination),
    )


def build_error_response(code: ErrorCode, message: str, details: Any = None) -> ResponseEnvelope[None]:
    """Helper to cleanly assemble a standardized error response envelope."""
    req_id = get_current_request_id()
    return ResponseEnvelope(
        success=False,
        message=message,
        data=None,
        error=ErrorDetails(code=code, details=details),
        meta=ResponseMeta(request_id=req_id, pagination=None),
    )


def build_pagination_meta(page: int, page_size: int, total_items: int) -> PaginationMeta:
    """Helper to construct pagination metadata objects."""
    import math

    total_pages = math.ceil(total_items / page_size) if total_items > 0 else 0
    return PaginationMeta(
        page=page,
        page_size=page_size,
        total_items=total_items,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_previous=page > 1,
    )
