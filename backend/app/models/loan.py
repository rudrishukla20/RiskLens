"""
Loan ORM model — 13.11
"""

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Loan(Base):
    __tablename__ = "loans"

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
    source_loan_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    loan_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    loan_purpose: Mapped[str | None] = mapped_column(String(255), nullable=True)
    interest_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    loan_term: Mapped[int | None] = mapped_column(Integer, nullable=True)  # months
    loan_status: Mapped[str | None] = mapped_column(String(100), nullable=True)
    disbursement_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    outstanding_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    annuity_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    repayment_burden_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    delinquency_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    historical_default_flag: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    asset_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    additional_attributes_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    dataset: Mapped["Dataset"] = relationship("Dataset", back_populates="loans", lazy="noload")
    version: Mapped["DatasetVersion"] = relationship("DatasetVersion", back_populates="loans", lazy="noload")
    borrower: Mapped["Borrower"] = relationship("Borrower", back_populates="loans", lazy="noload")

    def __repr__(self) -> str:
        return f"<Loan source_id={self.source_loan_id!r} amount={self.loan_amount}>"
