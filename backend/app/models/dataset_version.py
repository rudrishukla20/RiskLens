"""
DatasetVersion ORM model — 13.5
"""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class DatasetVersion(Base):
    __tablename__ = "dataset_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("datasets.id", ondelete="CASCADE", use_alter=True),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)  # SHA-256 hex
    schema_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    row_count: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    column_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    storage_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    dataset: Mapped["Dataset"] = relationship(
        "Dataset", back_populates="versions", foreign_keys=[dataset_id], lazy="noload"
    )
    files: Mapped[list["DatasetFile"]] = relationship("DatasetFile", back_populates="version", lazy="noload")
    raw_records: Mapped[list["RawRecord"]] = relationship("RawRecord", back_populates="version", lazy="noload")
    schema_mappings: Mapped[list["SchemaMapping"]] = relationship(
        "SchemaMapping", back_populates="version", lazy="noload"
    )
    validation_runs: Mapped[list["ValidationRun"]] = relationship(
        "ValidationRun", back_populates="version", lazy="noload"
    )
    profile_runs: Mapped[list["ProfileRun"]] = relationship("ProfileRun", back_populates="version", lazy="noload")
    borrowers: Mapped[list["Borrower"]] = relationship("Borrower", back_populates="version", lazy="noload")
    loans: Mapped[list["Loan"]] = relationship("Loan", back_populates="version", lazy="noload")

    def __repr__(self) -> str:
        return f"<DatasetVersion dataset_id={self.dataset_id!r} v={self.version_number}>"
