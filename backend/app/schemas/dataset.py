import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import Field

from app.enums.dataset_status import DatasetStatusEnum
from app.enums.file_type import FileTypeEnum
from app.enums.validation_status import ValidationStatusEnum
from app.schemas.common import BaseSchema, TimestampModel, UUIDModel


class DatasetVersionResponse(UUIDModel):
    """Dataset version historical log payload."""

    dataset_id: uuid.UUID
    version_number: int
    file_hash: Optional[str] = None
    schema_hash: Optional[str] = None
    row_count: Optional[int] = None
    column_count: Optional[int] = None
    storage_path: Optional[str] = None
    created_by: Optional[uuid.UUID] = None
    created_at: datetime


class DatasetColumnResponse(UUIDModel):
    """Inferred schema field metadata for UI mapping confirmation."""

    dataset_id: uuid.UUID
    version_id: Optional[uuid.UUID] = None
    original_column_name: str
    canonical_column_name: Optional[str] = None
    inferred_data_type: Optional[str] = None
    mapped_data_type: Optional[str] = None
    is_required: bool
    is_mapped: bool
    sample_values_json: Optional[List[Any]] = Field(default=None, serialization_alias="sample_values")
    created_at: datetime


class DatasetUploadResponse(UUIDModel):
    """Payload returned immediately following a file upload transaction."""

    name: str
    original_file_name: str
    file_type: FileTypeEnum
    upload_status: DatasetStatusEnum = Field(serialization_alias="status")
    uploaded_by: uuid.UUID
    created_at: datetime


class DatasetResponse(UUIDModel, TimestampModel):
    """Dataset summary details payload."""

    name: str
    description: Optional[str] = None
    source_type: Optional[str] = None
    original_file_name: str
    file_type: FileTypeEnum
    uploaded_by: uuid.UUID
    upload_status: DatasetStatusEnum
    validation_status: ValidationStatusEnum
    profiling_status: DatasetStatusEnum
    analysis_status: DatasetStatusEnum
    record_count: Optional[int] = None
    column_count: Optional[int] = None
    active_version_id: Optional[uuid.UUID] = None
    storage_path: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = Field(default=None, serialization_alias="metadata")
    archived_at: Optional[datetime] = None


class DatasetListResponse(BaseSchema):
    """List payload of datasets."""

    items: List[DatasetResponse]
    total: int
