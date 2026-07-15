import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.column_profile import ColumnProfile
from app.models.profiling import ProfileRun
from app.repositories.base import BaseRepository


class ProfilingRepository(BaseRepository[ProfileRun]):
    """Repository handling dataset profiling jobs summaries and statistical outputs."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(ProfileRun, db)

    # ── Profile Runs ──────────────────────────────────────────────────────────
    async def get_latest_run(self, dataset_id: uuid.UUID) -> Optional[ProfileRun]:
        """Queries the latest profiling execution completed for a dataset."""
        stmt = (
            select(self.model)
            .where(self.model.dataset_id == dataset_id)
            .order_by(self.model.started_at.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    # ── Column Profiles ───────────────────────────────────────────────────────
    async def get_column_profiles(self, run_id: uuid.UUID) -> List[ColumnProfile]:
        """Queries stats metrics configured for each field in a profile execution."""
        stmt = select(ColumnProfile).where(ColumnProfile.profile_run_id == run_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def bulk_create_column_profiles(self, profiles: List[ColumnProfile]) -> List[ColumnProfile]:
        """Inserts field profiles in bulk."""
        self.db.add_all(profiles)
        await self.db.flush()
        return profiles
