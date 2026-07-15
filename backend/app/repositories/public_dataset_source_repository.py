from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.public_dataset_source import PublicDatasetSource
from app.repositories.base import BaseRepository


class PublicDatasetSourceRepository(BaseRepository[PublicDatasetSource]):
    """Repository handling read-only queries against references datasets catalogue."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(PublicDatasetSource, db)

    async def get_active_sources(self) -> List[PublicDatasetSource]:
        """Queries all active reference catalog rows."""
        stmt = select(self.model).where(self.model.is_active)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_name(self, name: str) -> Optional[PublicDatasetSource]:
        """Queries a source catalog record by its name."""
        stmt = select(self.model).where(self.model.name == name)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
