import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.common import BaseSchema, UUIDModel


class SchemaMappingItem(BaseModel):
    """A single column schema mapping rule."""

    original_column_name: str = Field(description="The header name inside the uploaded raw dataset")
    canonical_field: str = Field(description="The target fields code name mapped from standard catalog")


class SchemaMappingConfirmRequest(BaseModel):
    """Payload to confirm/overwrite dataset column schema maps."""

    mappings: List[SchemaMappingItem] = Field(description="Active list of column mappings")


class SchemaMappingResponse(UUIDModel):
    """Schema mapping record details."""

    dataset_id: uuid.UUID
    version_id: Optional[uuid.UUID] = None
    original_column_name: str
    canonical_field: str
    confidence_score: Optional[float] = None
    mapping_source: str = Field(description="'AUTO' or 'MANUAL'")
    confirmed_by: Optional[uuid.UUID] = None
    confirmed_at: Optional[datetime] = None
    created_at: datetime


class SchemaMappingListResponse(BaseSchema):
    """Wrapper response for mapped columns."""

    items: List[SchemaMappingResponse]
    total: int
