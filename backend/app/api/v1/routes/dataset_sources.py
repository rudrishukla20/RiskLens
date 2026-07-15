import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_any_role
from app.models.user import User
from app.responses.envelope import ResponseEnvelope, build_success_response
from app.services.public_dataset_source_service import PublicDatasetSourceService

router = APIRouter()


class PublicDatasetSourceResponse(BaseModel):
    id: uuid.UUID
    name: str
    provider: Optional[str] = None
    source_url: Optional[str] = None
    dataset_category: Optional[str] = None
    access_type: Optional[str] = None
    recommended_use: Optional[str] = None
    notes: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True


@router.get("", response_model=ResponseEnvelope[List[PublicDatasetSourceResponse]])
async def list_public_dataset_sources(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(require_any_role)
):
    """
    Lists active reference third-party public data sources.
    """
    service = PublicDatasetSourceService(db)
    sources = await service.list_active_sources()
    responses = [PublicDatasetSourceResponse.model_validate(s) for s in sources]
    return build_success_response(data=responses, message="Public dataset sources retrieved successfully.")
