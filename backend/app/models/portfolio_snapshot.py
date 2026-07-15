"""
PortfolioSnapshot ORM model — 13.21
"""

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class PortfolioSnapshot(Base):
    __tablename__ = "portfolio_snapshots"

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
    portfolio_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_loans: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_borrowers: Mapped[int | None] = mapped_column(Integer, nullable=True)
    outstanding_exposure: Mapped[float | None] = mapped_column(Float, nullable=True)
    high_risk_exposure: Mapped[float | None] = mapped_column(Float, nullable=True)
    average_risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    average_loan_size: Mapped[float | None] = mapped_column(Float, nullable=True)
    concentration_index: Mapped[float | None] = mapped_column(Float, nullable=True)
    diversification_index: Mapped[float | None] = mapped_column(Float, nullable=True)
    snapshot_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    segment_metrics: Mapped[list["PortfolioSegmentMetric"]] = relationship(
        "PortfolioSegmentMetric",
        primaryjoin="PortfolioSegmentMetric.dataset_id == PortfolioSnapshot.dataset_id",
        foreign_keys="PortfolioSegmentMetric.dataset_id",
        lazy="noload",
        viewonly=True,
    )

    def __repr__(self) -> str:
        return (
            f"<PortfolioSnapshot dataset_id={self.dataset_id!r} "
            f"date={self.snapshot_date} value={self.portfolio_value}>"
        )
