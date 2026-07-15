"""
ValidationRun ORM model — 13.12
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums.validation_status import ValidationStatusEnum
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.dataset import Dataset
    from app.models.dataset_version import DatasetVersion
    from app.models.validation_issue import ValidationIssue


class ValidationRun(Base):
    __tablename__ = "validation_runs"

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
    total_records: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    valid_records: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    invalid_records: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    missing_value_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    duplicate_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    invalid_type_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    outlier_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    business_rule_violation_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    validation_score: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0.0–100.0
    status: Mapped[ValidationStatusEnum] = mapped_column(
        String(50), nullable=False, default=ValidationStatusEnum.PENDING
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    dataset: Mapped["Dataset"] = relationship("Dataset", back_populates="validation_runs", lazy="noload")
    version: Mapped["DatasetVersion"] = relationship("DatasetVersion", back_populates="validation_runs", lazy="noload")
    issues: Mapped[list["ValidationIssue"]] = relationship(
        "ValidationIssue", back_populates="validation_run", cascade="all, delete-orphan", lazy="noload"
    )

    def __repr__(self) -> str:
        return (
            f"<ValidationRun dataset_id={self.dataset_id!r} " f"score={self.validation_score} status={self.status!r}>"
        )
