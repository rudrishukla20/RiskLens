import uuid
from typing import List, Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schema_mapping import SchemaMapping
from app.repositories.base import BaseRepository


class SchemaMappingRepository(BaseRepository[SchemaMapping]):
    """Repository handling target columns mapping dictionary definitions."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(SchemaMapping, db)

    async def get_by_dataset(
        self, dataset_id: uuid.UUID, version_id: Optional[uuid.UUID] = None
    ) -> List[SchemaMapping]:
        """Queries column mappings rules configured for a dataset version."""
        stmt = select(self.model).where(self.model.dataset_id == dataset_id)
        if version_id:
            stmt = stmt.where(self.model.version_id == version_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def delete_by_dataset(self, dataset_id: uuid.UUID, version_id: Optional[uuid.UUID] = None) -> None:
        """Deletes previous mappings rules to prepare for mapping overrides."""
        stmt = delete(self.model).where(self.model.dataset_id == dataset_id)
        if version_id:
            stmt = stmt.where(self.model.version_id == version_id)
        await self.db.execute(stmt)
        await self.db.flush()
