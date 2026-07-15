"""
RiskMigrationCell ORM model — 13.25
"""

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.enums.risk_category import RiskCategoryEnum
from app.models.base import Base


class RiskMigrationCell(Base):
    __tablename__ = "risk_migration_cells"

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
    from_risk_category: Mapped[RiskCategoryEnum] = mapped_column(String(20), nullable=False)
    to_risk_category: Mapped[RiskCategoryEnum] = mapped_column(String(20), nullable=False)
    borrower_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    exposure_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    def __repr__(self) -> str:
        return (
            f"<RiskMigrationCell {self.from_risk_category!r} → {self.to_risk_category!r} "
            f"borrowers={self.borrower_count}>"
        )
