"""
ProfileRun ORM model — 13.14
"""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums.dataset_status import DatasetStatusEnum
from app.models.base import Base


class ProfileRun(Base):
    __tablename__ = "profile_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dataset_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    row_count: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    column_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    missing_percentage: Mapped[float | None] = mapped_column(Float, nullable=True)
    duplicate_percentage: Mapped[float | None] = mapped_column(Float, nullable=True)
    dataset_health_score: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0.0–100.0
    status: Mapped[DatasetStatusEnum] = mapped_column(String(50), nullable=False, default=DatasetStatusEnum.PROFILING)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    dataset: Mapped["Dataset"] = relationship("Dataset", back_populates="profile_runs", lazy="noload")
    version: Mapped["DatasetVersion"] = relationship("DatasetVersion", back_populates="profile_runs", lazy="noload")
    column_profiles: Mapped[list["ColumnProfile"]] = relationship(
        "ColumnProfile", back_populates="profile_run", cascade="all, delete-orphan", lazy="noload"
    )

    def __repr__(self) -> str:
        return (
            f"<ProfileRun dataset_id={self.dataset_id!r} " f"health={self.dataset_health_score} status={self.status!r}>"
        )
