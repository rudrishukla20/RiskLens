import os
import uuid
from typing import List, Optional

from app.core.config import settings
from app.exceptions.base import FileUploadException

# Standard MIME type mappings for allowed file types
MIME_TYPE_MAPPING = {
    ".csv": ["text/csv", "application/csv", "text/plain"],
    ".xlsx": ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/vnd.ms-excel"],
    ".json": ["application/json", "text/plain"],
    ".pdf": ["application/pdf"],
    ".docx": ["application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/msword"],
}


def validate_file_extension(filename: str, allowed_extensions: List[str]) -> str:
    """
    Validates that a filename extension resides within allowed extension bounds.
    Returns the normalized extension.
    """
    _, ext = os.path.splitext(filename.lower())
    if not ext or ext not in allowed_extensions:
        raise FileUploadException(
            message=f"File extension '{ext}' is not allowed. Allowed: {', '.join(allowed_extensions)}"
        )
    return ext


def validate_file_mime_type(ext: str, mime_type: Optional[str]) -> None:
    """Validates that the provided MIME type matches the file extension."""
    if not mime_type:
        return  # Allow if missing, but check if mapping exists

    allowed_mimes = MIME_TYPE_MAPPING.get(ext)
    if allowed_mimes and mime_type.lower() not in allowed_mimes:
        raise FileUploadException(message=f"Invalid MIME type '{mime_type}' for file extension '{ext}'.")


def validate_file_size(size_bytes: int) -> None:
    """Validates that the file size resides within maximum MB limits."""
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if size_bytes > max_bytes:
        raise FileUploadException(message=f"File size exceeds the limit of {settings.MAX_UPLOAD_SIZE_MB}MB.")


def generate_safe_filename(original_filename: str) -> str:
    """Generates a unique, path-safe filename using a UUID while preserving the extension."""
    _, ext = os.path.splitext(original_filename.lower())
    return f"{uuid.uuid4()}{ext}"


def sanitize_and_check_path(base_dir: str, filename: str) -> str:
    """
    Combines base directory with file name, validating upload path-traversal protection.
    Raises FileUploadException if path resolution attempts to escape the root directory.
    """
    # Clean filename of path segments to prevent injection
    safe_name = os.path.basename(filename)

    # Resolve absolute paths
    abs_base = os.path.abspath(base_dir)
    abs_target = os.path.abspath(os.path.join(abs_base, safe_name))

    # Verify target is nested within base directory
    if not abs_target.startswith(abs_base + os.sep) and abs_target != abs_base:
        raise FileUploadException(message="Path traversal attempt detected. Operation aborted.")

    return abs_target
