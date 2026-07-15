"""
RiskAssessment ORM model — 13.19
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums.risk_category import RiskCategoryEnum
from app.models.base import Base


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"

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
    borrower_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("borrowers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    loan_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("loans.id", ondelete="SET NULL"), nullable=True, index=True
    )
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)  # 0.0–100.0
    risk_category: Mapped[RiskCategoryEnum] = mapped_column(String(20), nullable=False)
    risk_driver_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    assessment_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    rule_set_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    driver_breakdowns: Mapped[list["RiskDriverBreakdown"]] = relationship(
        "RiskDriverBreakdown", back_populates="risk_assessment", cascade="all, delete-orphan", lazy="noload"
    )

    def __repr__(self) -> str:
        return (
            f"<RiskAssessment score={self.risk_score} " f"category={self.risk_category!r} v={self.assessment_version}>"
        )
