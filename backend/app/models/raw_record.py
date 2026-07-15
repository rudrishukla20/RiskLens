"""
RawRecord ORM model — 13.9
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums.validation_status import ValidationStatusEnum
from app.models.base import Base


class RawRecord(Base):
    __tablename__ = "raw_records"

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
    source_row_number: Mapped[int] = mapped_column(BigInteger, nullable=False)
    raw_data_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    canonical_data_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    validation_status: Mapped[ValidationStatusEnum] = mapped_column(
        String(50), nullable=False, default=ValidationStatusEnum.PENDING
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    dataset: Mapped["Dataset"] = relationship("Dataset", back_populates="raw_records", lazy="noload")
    version: Mapped["DatasetVersion"] = relationship("DatasetVersion", back_populates="raw_records", lazy="noload")

    def __repr__(self) -> str:
        return (
            f"<RawRecord dataset_id={self.dataset_id!r} "
            f"row={self.source_row_number} status={self.validation_status!r}>"
        )
