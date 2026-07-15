import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.enums.dataset_status import DatasetStatusEnum
from app.schemas.common import BaseSchema, UUIDModel


class DocumentUploadResponse(UUIDModel):
    """Payload returned immediately following a document file upload transaction."""

    dataset_id: Optional[uuid.UUID] = None
    original_file_name: str
    document_type: Optional[str] = None
    uploaded_by: Optional[uuid.UUID] = None
    upload_status: DatasetStatusEnum = Field(serialization_alias="status")
    created_at: datetime


class DocumentExtractionResponse(UUIDModel):
    """Raw texts and tables extracted from unstructured doc format."""

    document_id: uuid.UUID
    extracted_text: Optional[str] = None
    extracted_tables_json: Optional[List[Any]] = Field(default=None, serialization_alias="extracted_tables")
    metadata_json: Optional[Dict[str, Any]] = Field(default=None, serialization_alias="metadata")
    page_count: Optional[int] = None
    extraction_status: str
    created_at: datetime


class DocumentAnalysisResultResponse(UUIDModel):
    """Parsed structured metrics extracted from document context."""

    document_id: uuid.UUID
    executive_summary: Optional[str] = None
    key_findings_json: Optional[List[Any]] = Field(default=None, serialization_alias="key_findings")
    risk_notes_json: Optional[List[Any]] = Field(default=None, serialization_alias="risk_notes")
    compliance_observations_json: Optional[List[Any]] = Field(
        default=None, serialization_alias="compliance_observations"
    )
    extracted_financial_ratios_json: Optional[Dict[str, Any]] = Field(
        default=None, serialization_alias="extracted_financial_ratios"
    )
    created_at: datetime


class DocumentResponse(UUIDModel):
    """Document metadata details summary payload."""

    dataset_id: Optional[uuid.UUID] = None
    original_file_name: str
    document_type: Optional[str] = None
    uploaded_by: Optional[uuid.UUID] = None
    upload_status: DatasetStatusEnum
    analysis_status: DatasetStatusEnum
    storage_path: Optional[str] = None
    file_size_bytes: Optional[int] = None
    checksum_sha256: Optional[str] = None
    created_at: datetime
    extractions: Optional[List[DocumentExtractionResponse]] = None
    analysis_results: Optional[List[DocumentAnalysisResultResponse]] = None


class DocumentListResponse(BaseSchema):
    """List payload of documents."""

    items: List[DocumentResponse]
    total: int


class DocumentAnalyzeRequest(BaseModel):
    """Analysis request options."""

    run_ai_insights: bool = Field(default=True, description="Enable LLM extraction engine run")
