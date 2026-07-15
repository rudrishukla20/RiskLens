"""
PortfolioSegmentMetric ORM model — 13.22
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class PortfolioSegmentMetric(Base):
    __tablename__ = "portfolio_segment_metrics"

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
    segment_type: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g. "region", "employment_type"
    segment_value: Mapped[str] = mapped_column(String(255), nullable=False)  # e.g. "NORTH", "SALARIED"
    borrower_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    loan_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    portfolio_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    outstanding_exposure: Mapped[float | None] = mapped_column(Float, nullable=True)
    average_risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    high_risk_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    high_risk_exposure: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    def __repr__(self) -> str:
        return (
            f"<PortfolioSegmentMetric type={self.segment_type!r} "
            f"value={self.segment_value!r} loans={self.loan_count}>"
        )
