"""
Ingestion file validator — orchestrates extension, MIME, and size checks.

Delegates to utils/file.py helpers. Returns the validated FileTypeEnum
or raises FileUploadException.
"""

from typing import Optional

from app.enums.file_type import FileTypeEnum
from app.exceptions.base import FileUploadException
from app.utils.file import (
    validate_file_extension,
    validate_file_mime_type,
    validate_file_size,
)
from app.utils.validators import (
    get_allowed_document_extensions,
    get_allowed_structured_extensions,
    resolve_file_type_from_ext,
)


def validate_upload(
    filename: str,
    file_size_bytes: int,
    mime_type: Optional[str] = None,
    category: str = "structured",
) -> FileTypeEnum:
    """
    Full validation pass for an uploaded file.

    Parameters
    ----------
    filename : str
        Original client-side filename (e.g. ``"loans.csv"``).
    file_size_bytes : int
        Raw byte size of the uploaded file.
    mime_type : str | None
        Content-Type header value, if available.
    category : str
        ``"structured"`` for CSV/XLSX/JSON datasets, ``"document"`` for PDF/DOCX.

    Returns
    -------
    FileTypeEnum
        The resolved file type.

    Raises
    ------
    FileUploadException
        If any validation check fails.
    """
    # 1. File size
    validate_file_size(file_size_bytes)

    # 2. Extension
    if category == "document":
        allowed_exts = get_allowed_document_extensions()
    else:
        allowed_exts = get_allowed_structured_extensions()

    ext = validate_file_extension(filename, allowed_exts)

    # 3. MIME type
    validate_file_mime_type(ext, mime_type)

    # 4. Resolve type enum
    file_type = resolve_file_type_from_ext(ext)

    # 5. Image / unsupported guard
    if file_type not in (
        FileTypeEnum.CSV,
        FileTypeEnum.XLSX,
        FileTypeEnum.JSON,
        FileTypeEnum.PDF,
        FileTypeEnum.DOCX,
    ):
        raise FileUploadException(
            message=(
                f"File type '{file_type.value}' is not supported in this version. "
                "Supported types: CSV, XLSX, JSON, PDF, DOCX."
            )
        )

    return file_type
