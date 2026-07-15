"""
ColumnProfile ORM model — 13.15
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ColumnProfile(Base):
    __tablename__ = "column_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    profile_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("profile_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    column_name: Mapped[str] = mapped_column(String(255), nullable=False)
    data_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    missing_count: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    missing_percentage: Mapped[float | None] = mapped_column(Float, nullable=True)
    unique_count: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    mean_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    median_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    min_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    std_dev: Mapped[float | None] = mapped_column(Float, nullable=True)
    percentile_25: Mapped[float | None] = mapped_column(Float, nullable=True)
    percentile_75: Mapped[float | None] = mapped_column(Float, nullable=True)
    outlier_count: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    distribution_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    profile_run: Mapped["ProfileRun"] = relationship("ProfileRun", back_populates="column_profiles", lazy="noload")

    def __repr__(self) -> str:
        return f"<ColumnProfile column={self.column_name!r} type={self.data_type!r}>"
