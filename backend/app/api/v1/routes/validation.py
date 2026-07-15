import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_any_role
from app.models.user import User
from app.responses.envelope import ResponseEnvelope, build_success_response
from app.schemas.validation import (
    ValidationIssueResponse,
    ValidationRunResponse,
    ValidationRunTriggerResponse,
)
from app.services.dataset_service import DatasetService
from app.services.validation_service import ValidationService

router = APIRouter()


@router.post("/datasets/{dataset_id}/validate", response_model=ResponseEnvelope[ValidationRunTriggerResponse])
async def trigger_validation(
    dataset_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_any_role)
):
    """
    Triggers a data quality validation run asynchronously.
    """
    dataset_service = DatasetService(db, current_user)
    # Ensure dataset exists (raises 404)
    await dataset_service.get_dataset(dataset_id)

    service = ValidationService(db, current_user)
    try:
        run = await service.trigger_validation(dataset_id)
        await db.commit()

        data = ValidationRunTriggerResponse(validation_run_id=run.id, dataset_id=run.dataset_id, status=run.status)
        return build_success_response(data=data, message="Validation run triggered successfully.")
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/datasets/{dataset_id}/validation/latest", response_model=ResponseEnvelope[Optional[ValidationRunResponse]]
)
async def get_latest_validation(
    dataset_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_any_role)
):
    """
    Queries the latest validation run logs.
    """
    dataset_service = DatasetService(db, current_user)
    # Ensure dataset exists
    await dataset_service.get_dataset(dataset_id)

    service = ValidationService(db, current_user)
    run = await service.get_latest_run(dataset_id)
    if not run:
        return build_success_response(data=None, message="No validation run found for this dataset.")

    # Count severities from issues in database
    from sqlalchemy import select, func
    from app.models.validation_issue import ValidationIssue

    stmt_counts = (
        select(ValidationIssue.severity, func.count(ValidationIssue.id))
        .where(ValidationIssue.validation_run_id == run.id)
        .group_by(ValidationIssue.severity)
    )
    res_counts = await db.execute(stmt_counts)
    counts = {row[0]: row[1] for row in res_counts.all()}

    error_count = counts.get("ERROR", 0)
    warning_count = counts.get("WARNING", 0)
    info_count = counts.get("INFO", 0)

    data = ValidationRunResponse(
        id=run.id,
        dataset_id=run.dataset_id,
        version_id=run.version_id,
        total_records=run.total_records,
        valid_records=run.valid_records,
        invalid_records=run.invalid_records,
        missing_value_count=run.missing_value_count,
        duplicate_count=run.duplicate_count,
        invalid_type_count=run.invalid_type_count,
        outlier_count=run.outlier_count,
        business_rule_violation_count=run.business_rule_violation_count,
        validation_score=run.validation_score,
        status=run.status,
        started_at=run.started_at,
        completed_at=run.completed_at,
        created_by=run.created_by,
        error_count=error_count,
        warning_count=warning_count,
        info_count=info_count,
    )
    return build_success_response(data=data, message="Latest validation run retrieved successfully.")


@router.get("/datasets/{dataset_id}/validation/issues", response_model=ResponseEnvelope[List[ValidationIssueResponse]])
async def get_validation_issues(
    dataset_id: uuid.UUID,
    run_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_any_role),
):
    """
    Queries granular issues list for a run ID. Defaults to the latest validation run if run_id is omitted.
    """
    dataset_service = DatasetService(db, current_user)
    # Ensure dataset exists
    await dataset_service.get_dataset(dataset_id)

    service = ValidationService(db, current_user)
    target_run_id = run_id
    if not target_run_id:
        run = await service.get_latest_run(dataset_id)
        if not run:
            return build_success_response(data=[], message="No validation runs found for this dataset.")
        target_run_id = run.id

    issues = await service.get_validation_issues(target_run_id)
    responses = [
        ValidationIssueResponse(
            id=i.id,
            validation_run_id=i.validation_run_id,
            dataset_id=i.dataset_id,
            source_row_number=i.source_row_number,
            column_name=i.column_name,
            issue_type=i.issue_type,
            severity=i.severity,
            message=i.message,
            observed_value=i.observed_value,
            created_at=i.created_at,
        )
        for i in issues
    ]
    return build_success_response(data=responses, message="Validation issues retrieved successfully.")
