"""
DocumentAnalysisResult ORM model — 13.18
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class DocumentAnalysisResult(Base):
    __tablename__ = "document_analysis_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    executive_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_findings_json: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    risk_notes_json: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    compliance_observations_json: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    extracted_financial_ratios_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="analysis_results", lazy="noload")

    def __repr__(self) -> str:
        return f"<DocumentAnalysisResult document_id={self.document_id!r}>"
