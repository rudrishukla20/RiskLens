import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import log_audit_action
from app.enums.audit_action import AuditActionEnum
from app.enums.dataset_status import DatasetStatusEnum
from app.models.column_profile import ColumnProfile
from app.models.profiling import ProfileRun
from app.models.user import User
from app.repositories.dataset_repository import DatasetRepository
from app.repositories.profiling_repository import ProfilingRepository


class ProfilingService:
    """Service to schedule dataset profiling runs and retrieve statistical distributions."""

    def __init__(self, db: AsyncSession, user: User) -> None:
        self.db = db
        self.user = user
        self.dataset_repo = DatasetRepository(db)
        self.profiling_repo = ProfilingRepository(db)

    async def trigger_profiling(self, dataset_id: uuid.UUID) -> ProfileRun:
        """
        Triggers a profiling run.
        """
        dataset = await self.dataset_repo.get(dataset_id)
        if not dataset:
            raise ValueError("Dataset not found.")

        from app.analytics.profiling_engine import ProfilingEngine
        engine = ProfilingEngine(self.db)

        # Run profiling inline
        run = await engine.run_profiling(dataset_id, dataset.active_version_id, self.user.id)

        await log_audit_action(
            self.db,
            user_id=self.user.id,
            action=AuditActionEnum.PROFILING_RUN,
            module_name="dataset",
            resource_type="Dataset",
            resource_id=str(dataset_id),
            details={"profile_run_id": str(run.id)},
        )

        await self.db.flush()
        return run

    async def get_latest_run(self, dataset_id: uuid.UUID) -> Optional[ProfileRun]:
        """Queries the latest profile run log."""
        return await self.profiling_repo.get_latest_run(dataset_id)

    async def get_column_profiles(self, run_id: uuid.UUID) -> List[ColumnProfile]:
        """Queries statistical profiles configured for each column field."""
        return await self.profiling_repo.get_column_profiles(run_id)
