import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import log_audit_action
from app.enums.audit_action import AuditActionEnum
from app.enums.validation_status import ValidationStatusEnum
from app.models.user import User
from app.models.validation import ValidationRun
from app.models.validation_issue import ValidationIssue
from app.repositories.dataset_repository import DatasetRepository
from app.repositories.validation_repository import ValidationRepository


class ValidationService:
    """Service to schedule dataset data validation runs and retrieve rules violations."""

    def __init__(self, db: AsyncSession, user: User) -> None:
        self.db = db
        self.user = user
        self.dataset_repo = DatasetRepository(db)
        self.validation_repo = ValidationRepository(db)

    async def trigger_validation(self, dataset_id: uuid.UUID) -> ValidationRun:
        """
        Triggers a data quality validation run.
        """
        dataset = await self.dataset_repo.get(dataset_id)
        if not dataset:
            raise ValueError("Dataset not found.")

        from app.analytics.data_quality_engine import DataQualityEngine
        engine = DataQualityEngine(self.db)
        
        # Run validation inline
        run = await engine.run_validation(dataset_id, dataset.active_version_id, self.user.id)

        await log_audit_action(
            self.db,
            user_id=self.user.id,
            action=AuditActionEnum.VALIDATION_RUN,
            module_name="dataset",
            resource_type="Dataset",
            resource_id=str(dataset_id),
            details={"run_id": str(run.id)},
        )

        await self.db.flush()
        return run

    async def get_latest_run(self, dataset_id: uuid.UUID) -> Optional[ValidationRun]:
        """Queries the latest validation run logs."""
        return await self.validation_repo.get_latest_run(dataset_id)

    async def get_validation_issues(self, run_id: uuid.UUID) -> List[ValidationIssue]:
        """Queries granular issues for a run ID."""
        return await self.validation_repo.get_issues(run_id)
