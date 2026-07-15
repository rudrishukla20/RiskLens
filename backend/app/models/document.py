"""
Document ORM model — 13.16
"""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums.dataset_status import DatasetStatusEnum
from app.models.base import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    dataset_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("datasets.id", ondelete="SET NULL"), nullable=True, index=True
    )
    original_file_name: Mapped[str] = mapped_column(String(512), nullable=False)
    document_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    upload_status: Mapped[DatasetStatusEnum] = mapped_column(
        String(50), nullable=False, default=DatasetStatusEnum.UPLOADED
    )
    analysis_status: Mapped[DatasetStatusEnum] = mapped_column(
        String(50), nullable=False, default=DatasetStatusEnum.UPLOADED
    )
    storage_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    extractions: Mapped[list["DocumentExtraction"]] = relationship(
        "DocumentExtraction", back_populates="document", cascade="all, delete-orphan", lazy="noload"
    )
    analysis_results: Mapped[list["DocumentAnalysisResult"]] = relationship(
        "DocumentAnalysisResult", back_populates="document", cascade="all, delete-orphan", lazy="noload"
    )
    ai_insights: Mapped[list["AIInsight"]] = relationship(
        "AIInsight", back_populates="document", foreign_keys="AIInsight.document_id", lazy="noload"
    )

    def __repr__(self) -> str:
        return f"<Document file={self.original_file_name!r} type={self.document_type!r}>"
