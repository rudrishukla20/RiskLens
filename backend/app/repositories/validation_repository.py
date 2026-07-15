import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.raw_record import RawRecord
from app.models.validation import ValidationRun
from app.models.validation_issue import ValidationIssue
from app.repositories.base import BaseRepository


class ValidationRepository(BaseRepository[ValidationRun]):
    """Repository handling dataset data validation runs executions and logs."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(ValidationRun, db)

    # ── Validation Runs ───────────────────────────────────────────────────────
    async def get_latest_run(self, dataset_id: uuid.UUID) -> Optional[ValidationRun]:
        """Fetches the latest validation run for a dataset."""
        stmt = (
            select(self.model)
            .where(self.model.dataset_id == dataset_id)
            .order_by(self.model.started_at.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    # ── Validation Issues ─────────────────────────────────────────────────────
    async def get_issues(self, run_id: uuid.UUID) -> List[ValidationIssue]:
        """Queries granular rules violation logs for a specific run."""
        stmt = select(ValidationIssue).where(ValidationIssue.validation_run_id == run_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def bulk_create_issues(self, issues: List[ValidationIssue]) -> List[ValidationIssue]:
        """Inserts validation issues in bulk."""
        self.db.add_all(issues)
        await self.db.flush()
        return issues

    # ── Raw Records ───────────────────────────────────────────────────────────
    async def get_raw_records(
        self, dataset_id: uuid.UUID, version_id: Optional[uuid.UUID] = None, *, skip: int = 0, limit: int = 100
    ) -> List[RawRecord]:
        """Queries parsed raw rows for ingestion checks."""
        stmt = select(RawRecord).where(RawRecord.dataset_id == dataset_id)
        if version_id:
            stmt = stmt.where(RawRecord.version_id == version_id)
        stmt = stmt.offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def bulk_create_raw_records(self, records: List[RawRecord]) -> List[RawRecord]:
        """Inserts raw record objects in bulk."""
        self.db.add_all(records)
        await self.db.flush()
        return records
