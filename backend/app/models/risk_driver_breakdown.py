"""
RiskDriverBreakdown ORM model — 13.20
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class RiskDriverBreakdown(Base):
    __tablename__ = "risk_driver_breakdowns"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    risk_assessment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("risk_assessments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    driver_name: Mapped[str] = mapped_column(String(255), nullable=False)
    driver_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    driver_weight: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0.0–1.0
    contribution_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    risk_assessment: Mapped["RiskAssessment"] = relationship(
        "RiskAssessment", back_populates="driver_breakdowns", lazy="noload"
    )

    def __repr__(self) -> str:
        return (
            f"<RiskDriverBreakdown driver={self.driver_name!r} "
            f"weight={self.driver_weight} contribution={self.contribution_score}>"
        )
