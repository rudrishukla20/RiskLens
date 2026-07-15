import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums.analysis_type import AnalysisTypeEnum
from app.models.ai_insight import AIInsight
from app.repositories.base import BaseRepository


class AIInsightRepository(BaseRepository[AIInsight]):
    """Repository handling AI LLM commentary insights metadata logs."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(AIInsight, db)

    async def get_by_dataset(self, dataset_id: uuid.UUID) -> List[AIInsight]:
        """Queries AI insights generated for a specific dataset."""
        stmt = select(self.model).where(self.model.dataset_id == dataset_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_document(self, document_id: uuid.UUID) -> List[AIInsight]:
        """Queries AI insights generated for a specific document."""
        stmt = select(self.model).where(self.model.document_id == document_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_latest_by_type(
        self,
        analysis_type: AnalysisTypeEnum,
        dataset_id: Optional[uuid.UUID] = None,
        document_id: Optional[uuid.UUID] = None,
    ) -> Optional[AIInsight]:
        """Queries the latest generated AI insight filtered by analysis lenses."""
        stmt = select(self.model).where(self.model.analysis_type == analysis_type)
        if dataset_id:
            stmt = stmt.where(self.model.dataset_id == dataset_id)
        if document_id:
            stmt = stmt.where(self.model.document_id == document_id)

        stmt = stmt.order_by(self.model.created_at.desc()).limit(1)
        result = await self.db.execute(stmt)
        return result.scalars().first()
