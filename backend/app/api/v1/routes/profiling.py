import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_any_role
from app.models.user import User
from app.responses.envelope import ResponseEnvelope, build_success_response
from app.schemas.profiling import (
    ColumnProfileResponse,
    ProfileRunResponse,
    ProfileRunTriggerResponse,
)
from app.services.dataset_service import DatasetService
from app.services.profiling_service import ProfilingService

router = APIRouter()


@router.post("/datasets/{dataset_id}/profile", response_model=ResponseEnvelope[ProfileRunTriggerResponse])
async def trigger_profiling(
    dataset_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_any_role)
):
    """
    Triggers a profiling run asynchronously.
    """
    dataset_service = DatasetService(db, current_user)
    # Ensure dataset exists
    await dataset_service.get_dataset(dataset_id)

    service = ProfilingService(db, current_user)
    try:
        run = await service.trigger_profiling(dataset_id)
        await db.commit()

        data = ProfileRunTriggerResponse(profile_run_id=run.id, dataset_id=run.dataset_id, status=run.status)
        return build_success_response(data=data, message="Profiling run triggered successfully.")
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/datasets/{dataset_id}/profile/latest", response_model=ResponseEnvelope[Optional[ProfileRunResponse]])
async def get_latest_profiling(
    dataset_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_any_role)
):
    """
    Queries the latest profiling run summary log.
    """
    dataset_service = DatasetService(db, current_user)
    # Ensure dataset exists
    await dataset_service.get_dataset(dataset_id)

    service = ProfilingService(db, current_user)
    run = await service.get_latest_run(dataset_id)
    if not run:
        return build_success_response(data=None, message="No profiling run found for this dataset.")

    data = ProfileRunResponse(
        id=run.id,
        dataset_id=run.dataset_id,
        version_id=run.version_id,
        row_count=run.row_count,
        column_count=run.column_count,
        missing_percentage=run.missing_percentage,
        duplicate_percentage=run.duplicate_percentage,
        dataset_health_score=run.dataset_health_score,
        status=run.status,
        started_at=run.started_at,
        completed_at=run.completed_at,
        created_by=run.created_by,
    )
    return build_success_response(data=data, message="Latest profiling run retrieved successfully.")


@router.get("/datasets/{dataset_id}/profile/columns", response_model=ResponseEnvelope[List[ColumnProfileResponse]])
async def get_column_profiles(
    dataset_id: uuid.UUID,
    run_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_any_role),
):
    """
    Queries statistical profiles configured for each column field. Defaults to the latest profiling run if run_id is omitted.
    """
    dataset_service = DatasetService(db, current_user)
    # Ensure dataset exists
    await dataset_service.get_dataset(dataset_id)

    service = ProfilingService(db, current_user)
    target_run_id = run_id
    if not target_run_id:
        run = await service.get_latest_run(dataset_id)
        if not run:
            return build_success_response(data=[], message="No profiling runs found for this dataset.")
        target_run_id = run.id

    profiles = await service.get_column_profiles(target_run_id)
    responses = [
        ColumnProfileResponse(
            id=p.id,
            profile_run_id=p.profile_run_id,
            dataset_id=p.dataset_id,
            column_name=p.column_name,
            data_type=p.data_type,
            missing_count=p.missing_count,
            missing_percentage=p.missing_percentage,
            unique_count=p.unique_count,
            mean_value=p.mean_value,
            median_value=p.median_value,
            min_value=p.min_value,
            max_value=p.max_value,
            std_dev=p.std_dev,
            percentile_25=p.percentile_25,
            percentile_75=p.percentile_75,
            outlier_count=p.outlier_count,
            distribution=p.distribution_json,
            created_at=p.created_at,
        )
        for p in profiles
    ]
    return build_success_response(data=responses, message="Column profiles retrieved successfully.")
