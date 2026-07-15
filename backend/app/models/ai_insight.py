"""
AIInsight ORM model — 13.26
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums.analysis_type import AnalysisTypeEnum
from app.models.base import Base


class AIInsight(Base):
    __tablename__ = "ai_insights"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    dataset_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("datasets.id", ondelete="SET NULL"), nullable=True, index=True
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True, index=True
    )
    analysis_type: Mapped[AnalysisTypeEnum] = mapped_column(String(50), nullable=False, index=True)
    executive_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_findings_json: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    risk_observations_json: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    recommendations_json: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    source_metrics_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    provider: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # e.g. "openai" | "anthropic" | "rule_engine"
    model_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    generated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    document: Mapped["Document"] = relationship(
        "Document", back_populates="ai_insights", foreign_keys=[document_id], lazy="noload"
    )

    def __repr__(self) -> str:
        return f"<AIInsight type={self.analysis_type!r} " f"provider={self.provider!r} dataset_id={self.dataset_id!r}>"
