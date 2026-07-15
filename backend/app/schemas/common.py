import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BaseSchema(BaseModel):
    """Base Pydantic schema configured for SQLAlchemy ORM compatibility."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True, arbitrary_types_allowed=True)


class UUIDModel(BaseSchema):
    """Mixin for models containing a UUID primary key."""

    id: uuid.UUID = Field(description="Unique resource identifier")


class TimestampModel(BaseSchema):
    """Mixin for models containing audit timestamps."""

    created_at: datetime = Field(description="Resource creation timestamp")
    updated_at: datetime = Field(description="Resource last update timestamp")


class PaginationParams(BaseModel):
    """Pagination query request parameters."""

    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    size: int = Field(default=20, ge=1, le=100, description="Page size limit")
