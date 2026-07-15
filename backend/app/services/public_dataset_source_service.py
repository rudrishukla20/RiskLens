from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.public_dataset_source import PublicDatasetSource
from app.repositories.public_dataset_source_repository import PublicDatasetSourceRepository


class PublicDatasetSourceService:
    """Service retrieving reference catalog list elements."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.source_repo = PublicDatasetSourceRepository(db)

    async def list_active_sources(self) -> List[PublicDatasetSource]:
        """Lists active datasets references."""
        return await self.source_repo.get_active_sources()
