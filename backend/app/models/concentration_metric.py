"""
ConcentrationMetric ORM model — 13.23
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ConcentrationMetric(Base):
    __tablename__ = "concentration_metrics"

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
    concentration_type: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g. "region", "sector"
    concentration_key: Mapped[str] = mapped_column(String(255), nullable=False)  # e.g. "NORTH", "AGRICULTURE"
    exposure_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    exposure_percentage: Mapped[float | None] = mapped_column(Float, nullable=True)
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1 = most concentrated
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    def __repr__(self) -> str:
        return (
            f"<ConcentrationMetric type={self.concentration_type!r} "
            f"key={self.concentration_key!r} pct={self.exposure_percentage}>"
        )
