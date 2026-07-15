import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.enums.report_type import ReportTypeEnum
from app.schemas.common import BaseSchema, UUIDModel


class ReportGenerateRequest(BaseModel):
    """Configuration payload to construct a printable/exportable report PDF or XLSX."""

    dataset_id: Optional[uuid.UUID] = Field(default=None, description="Scope report context to a specific dataset")
    report_type: ReportTypeEnum = Field(description="Visual template style of report document")
    title: str = Field(max_length=512, description="Target report header title")
    export_format: str = Field(default="PDF", description="Format (PDF or XLSX)")
    custom_parameters: Optional[Dict[str, Any]] = Field(
        default=None, description="Dynamic key-value settings parameters"
    )


class ReportResponse(UUIDModel):
    """Generated document export details payload."""

    dataset_id: Optional[uuid.UUID] = None
    report_type: ReportTypeEnum
    title: str
    generated_by: Optional[uuid.UUID] = None
    export_format: str
    storage_path: Optional[str] = None
    report_metadata_json: Optional[Dict[str, Any]] = Field(default=None, serialization_alias="metadata")
    created_at: datetime


class ReportListResponse(BaseSchema):
    """List payload of reports."""

    items: List[ReportResponse]
    total: int


class ReportDownloadResponse(BaseModel):
    """Report file download response metadata."""

    report_id: uuid.UUID
    title: str
    export_format: str
    mime_type: str
    download_url: str
