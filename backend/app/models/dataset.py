"""
Dataset ORM model — 13.4
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums.dataset_status import DatasetStatusEnum
from app.enums.file_type import FileTypeEnum
from app.enums.validation_status import ValidationStatusEnum
from app.models.base import Base


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    original_file_name: Mapped[str] = mapped_column(String(512), nullable=False)
    file_type: Mapped[FileTypeEnum] = mapped_column(String(10), nullable=False)

    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    # Lifecycle status columns
    upload_status: Mapped[DatasetStatusEnum] = mapped_column(
        String(50), nullable=False, default=DatasetStatusEnum.UPLOADED
    )
    validation_status: Mapped[ValidationStatusEnum] = mapped_column(
        String(50), nullable=False, default=ValidationStatusEnum.PENDING
    )
    profiling_status: Mapped[DatasetStatusEnum] = mapped_column(
        String(50), nullable=False, default=DatasetStatusEnum.UPLOADED
    )
    analysis_status: Mapped[DatasetStatusEnum] = mapped_column(
        String(50), nullable=False, default=DatasetStatusEnum.UPLOADED
    )

    record_count: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    column_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Self-referential FK to the currently active version
    active_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dataset_versions.id", ondelete="SET NULL", use_alter=True),
        nullable=True,
    )

    storage_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    uploaded_by_user: Mapped["User"] = relationship(
        "User", back_populates="uploaded_datasets", foreign_keys=[uploaded_by], lazy="noload"
    )
    versions: Mapped[list["DatasetVersion"]] = relationship(
        "DatasetVersion",
        back_populates="dataset",
        foreign_keys="DatasetVersion.dataset_id",
        cascade="all, delete-orphan",
        lazy="noload",
    )
    files: Mapped[list["DatasetFile"]] = relationship(
        "DatasetFile", back_populates="dataset", cascade="all, delete-orphan", lazy="noload"
    )
    raw_records: Mapped[list["RawRecord"]] = relationship(
        "RawRecord", back_populates="dataset", cascade="all, delete-orphan", lazy="noload"
    )
    schema_mappings: Mapped[list["SchemaMapping"]] = relationship(
        "SchemaMapping", back_populates="dataset", cascade="all, delete-orphan", lazy="noload"
    )
    validation_runs: Mapped[list["ValidationRun"]] = relationship(
        "ValidationRun", back_populates="dataset", cascade="all, delete-orphan", lazy="noload"
    )
    profile_runs: Mapped[list["ProfileRun"]] = relationship(
        "ProfileRun", back_populates="dataset", cascade="all, delete-orphan", lazy="noload"
    )
    borrowers: Mapped[list["Borrower"]] = relationship(
        "Borrower", back_populates="dataset", cascade="all, delete-orphan", lazy="noload"
    )
    loans: Mapped[list["Loan"]] = relationship(
        "Loan", back_populates="dataset", cascade="all, delete-orphan", lazy="noload"
    )

    def __repr__(self) -> str:
        return f"<Dataset name={self.name!r} status={self.upload_status!r}>"
