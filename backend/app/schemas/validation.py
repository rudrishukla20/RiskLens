import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import Field

from app.enums.validation_status import ValidationStatusEnum
from app.schemas.common import BaseSchema, UUIDModel


class ValidationIssueResponse(UUIDModel):
    """Granular record level validation rule violation details."""

    validation_run_id: uuid.UUID
    dataset_id: uuid.UUID
    source_row_number: Optional[int] = None
    column_name: Optional[str] = None
    issue_type: str = Field(description="Code for validation failure (e.g. MISSING_VALUE, TYPE_MISMATCH)")
    severity: str = Field(description="Severity (e.g. ERROR, WARNING)")
    message: str
    observed_value: Optional[str] = None
    created_at: datetime


class ValidationRunResponse(UUIDModel):
    """Aggregate statistics for a complete data quality validation run execution."""

    dataset_id: uuid.UUID
    version_id: Optional[uuid.UUID] = None
    total_records: int
    valid_records: int
    invalid_records: int
    missing_value_count: int
    duplicate_count: int
    invalid_type_count: int
    outlier_count: int
    business_rule_violation_count: int
    validation_score: Optional[float] = None
    status: ValidationStatusEnum
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_by: Optional[uuid.UUID] = None
    error_count: int = 0
    warning_count: int = 0
    info_count: int = 0
    issues: Optional[List[ValidationIssueResponse]] = None


class ValidationRunTriggerResponse(BaseSchema):
    """Response returned immediately after triggering a validation task asynchronous."""

    validation_run_id: uuid.UUID = Field(serialization_alias="run_id")
    dataset_id: uuid.UUID
    status: ValidationStatusEnum
