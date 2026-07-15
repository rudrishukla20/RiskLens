"""
Report ORM model — 13.27
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.enums.report_type import ReportTypeEnum
from app.models.base import Base


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    dataset_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("datasets.id", ondelete="SET NULL"), nullable=True, index=True
    )
    report_type: Mapped[ReportTypeEnum] = mapped_column(String(60), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    generated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    export_format: Mapped[str] = mapped_column(String(10), nullable=False, default="PDF")  # "PDF" | "XLSX"
    storage_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    report_metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    def __repr__(self) -> str:
        return f"<Report type={self.report_type!r} title={self.title!r} format={self.export_format!r}>"
