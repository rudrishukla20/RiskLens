"""
DatasetColumn ORM model — required per monorepo structure.

Stores per-column metadata from inferred and confirmed schema mappings,
including sample values and canonical field alignment.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class DatasetColumn(Base):
    __tablename__ = "dataset_columns"

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
    original_column_name: Mapped[str] = mapped_column(String(255), nullable=False)
    canonical_column_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    inferred_data_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    mapped_data_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_mapped: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sample_values_json: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    dataset: Mapped["Dataset"] = relationship("Dataset", lazy="noload")
    version: Mapped["DatasetVersion"] = relationship("DatasetVersion", lazy="noload")

    def __repr__(self) -> str:
        return f"<DatasetColumn original={self.original_column_name!r} " f"canonical={self.canonical_column_name!r}>"
