"""
TrendMetric ORM model — 13.24
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class TrendMetric(Base):
    __tablename__ = "trend_metrics"

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
    metric_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    period_type: Mapped[str] = mapped_column(String(20), nullable=False)  # "MONTHLY" | "QUARTERLY" | "YEARLY"
    period_value: Mapped[str] = mapped_column(String(20), nullable=False)  # e.g. "2024-Q1", "2024-03", "2024"
    metric_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    dimension_name: Mapped[str | None] = mapped_column(String(100), nullable=True)  # optional slice dimension
    dimension_value: Mapped[str | None] = mapped_column(String(255), nullable=True)  # e.g. "HIGH_RISK"
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    def __repr__(self) -> str:
        return f"<TrendMetric metric={self.metric_name!r} " f"period={self.period_value!r} value={self.metric_value}>"
