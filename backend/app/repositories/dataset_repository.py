import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dataset import Dataset
from app.models.dataset_column import DatasetColumn
from app.models.dataset_file import DatasetFile
from app.models.dataset_version import DatasetVersion
from app.repositories.base import BaseRepository


class DatasetRepository(BaseRepository[Dataset]):
    """Repository managing structured datasets, versions, and physical files maps."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Dataset, db)

    # ── Dataset Versions ──────────────────────────────────────────────────────
    async def get_version(self, version_id: uuid.UUID) -> Optional[DatasetVersion]:
        """Fetches a specific historical dataset version record."""
        stmt = select(DatasetVersion).where(DatasetVersion.id == version_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_version_by_number(self, dataset_id: uuid.UUID, version_number: int) -> Optional[DatasetVersion]:
        """Queries a dataset version by its serial number."""
        stmt = select(DatasetVersion).where(
            DatasetVersion.dataset_id == dataset_id, DatasetVersion.version_number == version_number
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_version(self, version_obj: DatasetVersion) -> DatasetVersion:
        """Inserts a new dataset version record."""
        self.db.add(version_obj)
        await self.db.flush()
        return version_obj

    # ── Dataset Files ─────────────────────────────────────────────────────────
    async def create_file(self, file_obj: DatasetFile) -> DatasetFile:
        """Saves physical file storage path reference metadata."""
        self.db.add(file_obj)
        await self.db.flush()
        return file_obj

    async def get_file_by_checksum(self, checksum: str) -> Optional[DatasetFile]:
        """Checks for existing files using their SHA256 checksum signature."""
        stmt = select(DatasetFile).where(DatasetFile.checksum_sha256 == checksum)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    # ── Dataset Columns ───────────────────────────────────────────────────────
    async def get_columns(self, dataset_id: uuid.UUID, version_id: Optional[uuid.UUID] = None) -> List[DatasetColumn]:
        """Fetches columns metadata definitions mapped for a dataset version."""
        stmt = select(DatasetColumn).where(DatasetColumn.dataset_id == dataset_id)
        if version_id:
            stmt = stmt.where(DatasetColumn.version_id == version_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def bulk_create_columns(self, columns: List[DatasetColumn]) -> List[DatasetColumn]:
        """Performs bulk insertion of parsed column fields definitions."""
        self.db.add_all(columns)
        await self.db.flush()
        return columns
