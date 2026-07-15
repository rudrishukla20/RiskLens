import os
import shutil
import tempfile
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_any_role
from app.core.rate_limit import LIMIT_UPLOAD, limiter
from app.models.dataset import Dataset
from app.models.dataset_version import DatasetVersion
from app.models.user import User
from app.responses.envelope import ResponseEnvelope, build_success_response
from app.schemas.dataset import (
    DatasetColumnResponse,
    DatasetListResponse,
    DatasetResponse,
    DatasetUploadResponse,
    DatasetVersionResponse,
)
from app.services.dataset_service import DatasetService

router = APIRouter()


@router.post("/upload", response_model=ResponseEnvelope[DatasetUploadResponse], status_code=status.HTTP_201_CREATED)
@limiter.limit(LIMIT_UPLOAD)
async def upload_dataset(
    request: Request,
    name: str = Form(...),
    description: Optional[str] = Form(None),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_any_role),
):
    """
    Creates a new dataset record, uploads the file, and triggers schema parsing.
    """
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        shutil.copyfileobj(file.file, tmp)
        temp_path = tmp.name

    file_size = os.path.getsize(temp_path)

    try:
        service = DatasetService(db, current_user)
        dataset = await service.upload_dataset(
            name=name,
            original_filename=file.filename,
            file_size_bytes=file_size,
            temp_file_path=temp_path,
            description=description,
        )
        await db.commit()

        # Load relationships/attributes
        data = DatasetUploadResponse(
            id=dataset.id,
            name=dataset.name,
            original_file_name=dataset.original_file_name,
            file_type=dataset.file_type,
            upload_status=dataset.upload_status,
            uploaded_by=dataset.uploaded_by,
            created_at=dataset.created_at,
        )

        return build_success_response(data=data, message="Dataset uploaded successfully.")
    except Exception as e:
        await db.rollback()
        raise e
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


@router.get("", response_model=ResponseEnvelope[DatasetListResponse])
async def list_datasets(
    skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_any_role)
):
    """
    Lists metadata catalogs of active datasets.
    """
    service = DatasetService(db, current_user)
    datasets = await service.list_datasets(skip=skip, limit=limit)

    total_stmt = select(func.count()).select_from(Dataset).where(Dataset.archived_at.is_(None))
    total = (await db.execute(total_stmt)).scalar() or 0

    dataset_responses = [
        DatasetResponse(
            id=d.id,
            name=d.name,
            description=d.description,
            source_type=d.source_type,
            original_file_name=d.original_file_name,
            file_type=d.file_type,
            uploaded_by=d.uploaded_by,
            upload_status=d.upload_status,
            validation_status=d.validation_status,
            profiling_status=d.profiling_status,
            analysis_status=d.analysis_status,
            record_count=d.record_count,
            column_count=d.column_count,
            active_version_id=d.active_version_id,
            storage_path=d.storage_path,
            metadata=d.metadata_json,
            archived_at=d.archived_at,
            created_at=d.created_at,
            updated_at=d.updated_at,
        )
        for d in datasets
    ]

    return build_success_response(
        data=DatasetListResponse(items=dataset_responses, total=total), message="Datasets retrieved successfully."
    )


@router.get("/{dataset_id}", response_model=ResponseEnvelope[DatasetResponse])
async def get_dataset(
    dataset_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_any_role)
):
    """
    Fetches catalog metadata details for a specific dataset.
    """
    service = DatasetService(db, current_user)
    d = await service.get_dataset(dataset_id)

    data = DatasetResponse(
        id=d.id,
        name=d.name,
        description=d.description,
        source_type=d.source_type,
        original_file_name=d.original_file_name,
        file_type=d.file_type,
        uploaded_by=d.uploaded_by,
        upload_status=d.upload_status,
        validation_status=d.validation_status,
        profiling_status=d.profiling_status,
        analysis_status=d.analysis_status,
        record_count=d.record_count,
        column_count=d.column_count,
        active_version_id=d.active_version_id,
        storage_path=d.storage_path,
        metadata=d.metadata_json,
        archived_at=d.archived_at,
        created_at=d.created_at,
        updated_at=d.updated_at,
    )
    return build_success_response(data=data, message="Dataset details retrieved successfully.")


@router.delete("/{dataset_id}", response_model=ResponseEnvelope[DatasetResponse])
async def delete_dataset(
    dataset_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_any_role)
):
    """
    Archives/deletes a dataset by marking its archived_at timestamp.
    """
    service = DatasetService(db, current_user)
    d = await service.archive_dataset(dataset_id)
    await db.refresh(d)

    data = DatasetResponse(
        id=d.id,
        name=d.name,
        description=d.description,
        source_type=d.source_type,
        original_file_name=d.original_file_name,
        file_type=d.file_type,
        uploaded_by=d.uploaded_by,
        upload_status=d.upload_status,
        validation_status=d.validation_status,
        profiling_status=d.profiling_status,
        analysis_status=d.analysis_status,
        record_count=d.record_count,
        column_count=d.column_count,
        active_version_id=d.active_version_id,
        storage_path=d.storage_path,
        metadata=d.metadata_json,
        archived_at=d.archived_at,
        created_at=d.created_at,
        updated_at=d.updated_at,
    )
    await db.commit()
    return build_success_response(data=data, message="Dataset archived successfully.")


@router.get("/{dataset_id}/versions", response_model=ResponseEnvelope[List[DatasetVersionResponse]])
async def list_dataset_versions(
    dataset_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_any_role)
):
    """
    Lists historical dataset version logs for a specific dataset.
    """
    service = DatasetService(db, current_user)
    # Ensure dataset exists (will raise 404 if not)
    await service.get_dataset(dataset_id)

    stmt = (
        select(DatasetVersion)
        .where(DatasetVersion.dataset_id == dataset_id)
        .order_by(DatasetVersion.version_number.asc())
    )
    res = await db.execute(stmt)
    versions = res.scalars().all()

    data = [
        DatasetVersionResponse(
            id=v.id,
            dataset_id=v.dataset_id,
            version_number=v.version_number,
            file_hash=v.file_hash,
            schema_hash=v.schema_hash,
            row_count=v.row_count,
            column_count=v.column_count,
            storage_path=v.storage_path,
            created_by=v.created_by,
            created_at=v.created_at,
        )
        for v in versions
    ]
    return build_success_response(data=data, message="Dataset versions retrieved successfully.")


@router.get("/{dataset_id}/columns", response_model=ResponseEnvelope[List[DatasetColumnResponse]])
async def get_dataset_columns(
    dataset_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_any_role)
):
    """
    Lists parsed column metadata configured for a dataset version.
    """
    service = DatasetService(db, current_user)
    columns = await service.get_columns(dataset_id)

    data = [
        DatasetColumnResponse(
            id=c.id,
            dataset_id=c.dataset_id,
            version_id=c.version_id,
            original_column_name=c.original_column_name,
            canonical_column_name=c.canonical_column_name,
            inferred_data_type=c.inferred_data_type,
            mapped_data_type=c.mapped_data_type,
            is_required=c.is_required,
            is_mapped=c.is_mapped,
            sample_values=c.sample_values_json,
            created_at=c.created_at,
        )
        for c in columns
    ]
    return build_success_response(data=data, message="Dataset columns retrieved successfully.")


@router.post("/{dataset_id}/versions/upload", response_model=ResponseEnvelope[DatasetVersionResponse], status_code=status.HTTP_201_CREATED)
@limiter.limit(LIMIT_UPLOAD)
async def upload_dataset_version(
    request: Request,
    dataset_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_any_role),
):
    """
    Creates a new dataset version under an existing dataset, uploads the file, and triggers the transformations.
    """
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        shutil.copyfileobj(file.file, tmp)
        temp_path = tmp.name

    file_size = os.path.getsize(temp_path)

    try:
        service = DatasetService(db, current_user)
        version = await service.upload_dataset_version(
            dataset_id=dataset_id,
            original_filename=file.filename,
            file_size_bytes=file_size,
            temp_file_path=temp_path,
        )
        await db.commit()

        data = DatasetVersionResponse(
            id=version.id,
            dataset_id=version.dataset_id,
            version_number=version.version_number,
            file_hash=version.file_hash,
            schema_hash=version.schema_hash,
            row_count=version.row_count,
            column_count=version.column_count,
            storage_path=version.storage_path,
            created_by=version.created_by,
            created_at=version.created_at,
        )

        return build_success_response(data=data, message="Dataset version uploaded successfully.")
    except Exception as e:
        await db.rollback()
        raise e
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
