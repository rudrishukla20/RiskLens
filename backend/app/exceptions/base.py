from typing import Any, Optional

from app.responses.errors import ErrorCode


class AppException(Exception):
    """Base application exception for all managed domain errors."""

    status_code: int = 500
    error_code: ErrorCode = ErrorCode.INTERNAL_SERVER_ERROR
    message: str = "An unexpected error occurred."

    def __init__(
        self,
        message: Optional[str] = None,
        details: Any = None,
        status_code: Optional[int] = None,
        error_code: Optional[ErrorCode] = None,
    ) -> None:
        super().__init__(message or self.message)
        if message:
            self.message = message
        if status_code is not None:
            self.status_code = status_code
        if error_code is not None:
            self.error_code = error_code
        self.details = details


class ValidationException(AppException):
    """Exception representing request parameter or field validation failure."""

    status_code: int = 422
    error_code: ErrorCode = ErrorCode.VALIDATION_ERROR
    message: str = "Validation failed for request parameters."


class AuthenticationException(AppException):
    """Exception representing authentication credentials failure."""

    status_code: int = 401
    error_code: ErrorCode = ErrorCode.AUTH_UNAUTHORIZED
    message: str = "Authentication token is missing or invalid."


class AuthorizationException(AppException):
    """Exception representing user role permission failures."""

    status_code: int = 403
    error_code: ErrorCode = ErrorCode.AUTH_FORBIDDEN
    message: str = "You do not have permission to access this resource."


class NotFoundException(AppException):
    """Exception representing request for resource that does not exist."""

    status_code: int = 404
    error_code: ErrorCode = ErrorCode.NOT_FOUND
    message: str = "Requested resource not found."


class ConflictException(AppException):
    """Exception representing state conflict failures (e.g. duplicate keys)."""

    status_code: int = 409
    error_code: ErrorCode = ErrorCode.CONFLICT
    message: str = "State conflict with existing record."


class RateLimitException(AppException):
    """Exception representing API throttling rate limits exceeded."""

    status_code: int = 429
    error_code: ErrorCode = ErrorCode.RATE_LIMIT_EXCEEDED
    message: str = "Rate limit exceeded. Please try again later."


class FileUploadException(AppException):
    """Exception representing errors during document/dataset upload ingestion."""

    status_code: int = 400
    error_code: ErrorCode = ErrorCode.UPLOAD_ERROR
    message: str = "File upload failed or invalid file format."


class DatasetException(AppException):
    """Exception representing structured dataset schema/state failures."""

    status_code: int = 400
    error_code: ErrorCode = ErrorCode.BAD_REQUEST
    message: str = "Invalid dataset state or schema rules."


class SchemaMappingException(AppException):
    """Exception representing mapping failures of raw headers to canonical fields."""

    status_code: int = 400
    error_code: ErrorCode = ErrorCode.BAD_REQUEST
    message: str = "Schema column mapping failed."


class AnalyticsException(AppException):
    """Exception representing analytical engines runtime failures."""

    status_code: int = 400
    error_code: ErrorCode = ErrorCode.ANALYTICS_ERROR
    message: str = "Analytics calculations failure occurred."


class DocumentProcessingException(AppException):
    """Exception representing parser or OCR failures on unstructured text."""

    status_code: int = 400
    error_code: ErrorCode = ErrorCode.DOCUMENT_PROCESSING_ERROR
    message: str = "Failed to parse compliance document text."


class ReportGenerationException(AppException):
    """Exception representing errors compiling PDF/XLSX export files."""

    status_code: int = 400
    error_code: ErrorCode = ErrorCode.BAD_REQUEST
    message: str = "Failed to generate report export."


class ExternalAIException(AppException):
    """Exception representing failures communicating with external LLM API endpoints."""

    status_code: int = 502
    error_code: ErrorCode = ErrorCode.INTERNAL_SERVER_ERROR
    message: str = "Failed to communicate with external AI service."
