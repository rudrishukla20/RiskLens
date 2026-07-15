import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_any_role
from app.models.user import User
from app.repositories.schema_mapping_repository import SchemaMappingRepository
from app.responses.envelope import ResponseEnvelope, build_success_response
from app.schemas.schema_mapping import (
    SchemaMappingConfirmRequest,
    SchemaMappingResponse,
)
from app.services.dataset_service import DatasetService
from app.services.schema_mapping_service import SchemaMappingService

router = APIRouter()


@router.get("/datasets/{dataset_id}/schema-mapping", response_model=ResponseEnvelope[List[SchemaMappingResponse]])
async def get_schema_mapping(
    dataset_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_any_role)
):
    """
    Fetches the confirmed schema mappings configuration for the active version of a dataset.
    """
    dataset_service = DatasetService(db, current_user)
    # Ensure dataset exists (raises 404 if not found)
    dataset = await dataset_service.get_dataset(dataset_id)

    repo = SchemaMappingRepository(db)
    mappings = await repo.get_by_dataset(dataset_id, dataset.active_version_id)

    responses = [
        SchemaMappingResponse(
            id=m.id,
            dataset_id=m.dataset_id,
            version_id=m.version_id,
            original_column_name=m.original_column_name,
            canonical_field=m.canonical_field,
            confidence_score=m.confidence_score,
            mapping_source=m.mapping_source,
            confirmed_by=m.confirmed_by,
            confirmed_at=m.confirmed_at,
            created_at=m.created_at,
        )
        for m in mappings
    ]

    return build_success_response(data=responses, message="Schema mappings retrieved successfully.")


@router.post(
    "/datasets/{dataset_id}/schema-mapping/confirm", response_model=ResponseEnvelope[List[SchemaMappingResponse]]
)
async def confirm_schema_mappings(
    dataset_id: uuid.UUID,
    body: SchemaMappingConfirmRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_any_role),
):
    """
    Overwrites/saves the canonical mapping rules list for a dataset version.
    """
    dataset_service = DatasetService(db, current_user)
    # Ensure dataset exists (raises 404 if not found)
    await dataset_service.get_dataset(dataset_id)

    # Convert Pydantic request to dictionary format expected by the service
    confirmed_list = [
        {"original_column_name": item.original_column_name, "canonical_field": item.canonical_field}
        for item in body.mappings
    ]

    try:
        service = SchemaMappingService(db, current_user)
        saved = await service.confirm_mappings(dataset_id, confirmed_list)
        await db.commit()

        responses = [
            SchemaMappingResponse(
                id=m.id,
                dataset_id=m.dataset_id,
                version_id=m.version_id,
                original_column_name=m.original_column_name,
                canonical_field=m.canonical_field,
                confidence_score=m.confidence_score,
                mapping_source=m.mapping_source,
                confirmed_by=m.confirmed_by,
                confirmed_at=m.confirmed_at,
                created_at=m.created_at,
            )
            for m in saved
        ]

        return build_success_response(data=responses, message="Schema mappings confirmed successfully.")
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise e
