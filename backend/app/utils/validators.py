from typing import List

from app.core.config import settings
from app.enums.file_type import FileTypeEnum
from app.exceptions.base import FileUploadException
from app.utils.file import validate_file_extension


def get_allowed_structured_extensions() -> List[str]:
    """Retrieves allowed structured dataset extensions as a list."""
    return [ext.strip().lower() for ext in settings.ALLOWED_STRUCTURED_EXTENSIONS.split(",") if ext.strip()]


def get_allowed_document_extensions() -> List[str]:
    """Retrieves allowed compliance document extensions as a list."""
    return [ext.strip().lower() for ext in settings.ALLOWED_DOCUMENT_EXTENSIONS.split(",") if ext.strip()]


def is_structured_dataset(file_type: FileTypeEnum) -> bool:
    """Returns True if the FileTypeEnum represents a structured tabular dataset."""
    return file_type in (FileTypeEnum.CSV, FileTypeEnum.XLSX, FileTypeEnum.JSON)


def is_compliance_document(file_type: FileTypeEnum) -> bool:
    """Returns True if the FileTypeEnum represents an unstructured compliance document."""
    return file_type in (FileTypeEnum.PDF, FileTypeEnum.DOCX)


def resolve_file_type_from_ext(ext: str) -> FileTypeEnum:
    """Maps a file extension string (e.g. '.csv') to a standard FileTypeEnum value."""
    ext_clean = ext.lower().strip()
    if ext_clean == ".csv":
        return FileTypeEnum.CSV
    elif ext_clean in (".xlsx", ".xls"):
        return FileTypeEnum.XLSX
    elif ext_clean == ".json":
        return FileTypeEnum.JSON
    elif ext_clean == ".pdf":
        return FileTypeEnum.PDF
    elif ext_clean == ".docx":
        return FileTypeEnum.DOCX
    else:
        raise FileUploadException(message=f"Unsupported file type extension: {ext}")


def validate_structured_file(filename: str) -> FileTypeEnum:
    """Validates structured datasets extension and returns its FileTypeEnum."""
    allowed = get_allowed_structured_extensions()
    ext = validate_file_extension(filename, allowed)
    return resolve_file_type_from_ext(ext)


def validate_document_file(filename: str) -> FileTypeEnum:
    """Validates compliance documents extension and returns its FileTypeEnum."""
    allowed = get_allowed_document_extensions()
    ext = validate_file_extension(filename, allowed)
    return resolve_file_type_from_ext(ext)
