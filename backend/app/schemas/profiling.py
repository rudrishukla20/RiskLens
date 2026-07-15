import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import Field

from app.enums.dataset_status import DatasetStatusEnum
from app.schemas.common import BaseSchema, UUIDModel


class ColumnProfileResponse(UUIDModel):
    """Detailed summary statistics compiled for a single dataset field column."""

    profile_run_id: uuid.UUID
    dataset_id: uuid.UUID
    column_name: str
    data_type: Optional[str] = None
    missing_count: Optional[int] = None
    missing_percentage: Optional[float] = None
    unique_count: Optional[int] = None
    mean_value: Optional[float] = None
    median_value: Optional[float] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    std_dev: Optional[float] = None
    percentile_25: Optional[float] = None
    percentile_75: Optional[float] = None
    outlier_count: Optional[int] = None
    distribution_json: Optional[Dict[str, Any]] = Field(default=None, alias="distribution")
    created_at: datetime


class ProfileRunResponse(UUIDModel):
    """Aggregated metadata metrics from a dataset schema profiling run execution."""

    dataset_id: uuid.UUID
    version_id: Optional[uuid.UUID] = None
    row_count: Optional[int] = None
    column_count: Optional[int] = None
    missing_percentage: Optional[float] = None
    duplicate_percentage: Optional[float] = None
    dataset_health_score: Optional[float] = None
    status: DatasetStatusEnum
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_by: Optional[uuid.UUID] = None
    column_profiles: Optional[List[ColumnProfileResponse]] = None


class ProfileRunTriggerResponse(BaseSchema):
    """Response returned immediately after scheduling a dataset profiling background job."""

    profile_run_id: uuid.UUID = Field(serialization_alias="run_id")
    dataset_id: uuid.UUID
    status: DatasetStatusEnum
