import uuid
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums.report_type import ReportTypeEnum
from app.models.report import Report
from app.repositories.base import BaseRepository


class ReportRepository(BaseRepository[Report]):
    """Repository handling PDF/XLSX generated report metadata log logs."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Report, db)

    async def get_by_dataset(self, dataset_id: uuid.UUID) -> List[Report]:
        """Queries reports compiled for a specific dataset."""
        stmt = select(self.model).where(self.model.dataset_id == dataset_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_type(self, report_type: ReportTypeEnum) -> List[Report]:
        """Queries reports matching a specific category template code."""
        stmt = select(self.model).where(self.model.report_type == report_type)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
