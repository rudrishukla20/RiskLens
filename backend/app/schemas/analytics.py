import uuid
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import Field

from app.enums.risk_category import RiskCategoryEnum
from app.schemas.common import BaseSchema, UUIDModel


class BorrowerAnalyticsResponse(UUIDModel):
    """Borrower demographic details metrics payload."""

    dataset_id: uuid.UUID
    version_id: Optional[uuid.UUID] = None
    source_borrower_id: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    income: Optional[float] = None
    employment_type: Optional[str] = None
    education_level: Optional[str] = None
    marital_status: Optional[str] = None
    region: Optional[str] = None
    occupation: Optional[str] = None
    housing_type: Optional[str] = None
    family_size: Optional[int] = None
    additional_attributes_json: Optional[Dict[str, Any]] = Field(
        default=None, serialization_alias="additional_attributes"
    )
    created_at: datetime


class LoanAnalyticsResponse(UUIDModel):
    """Loan financial details parameters payload."""

    dataset_id: uuid.UUID
    version_id: Optional[uuid.UUID] = None
    borrower_id: Optional[uuid.UUID] = None
    source_loan_id: Optional[str] = None
    loan_amount: Optional[float] = None
    loan_purpose: Optional[str] = None
    interest_rate: Optional[float] = None
    loan_term: Optional[int] = None
    loan_status: Optional[str] = None
    disbursement_date: Optional[date] = None
    outstanding_amount: Optional[float] = None
    annuity_amount: Optional[float] = None
    repayment_burden_ratio: Optional[float] = None
    delinquency_days: Optional[int] = None
    historical_default_flag: Optional[bool] = None
    asset_value: Optional[float] = None
    additional_attributes_json: Optional[Dict[str, Any]] = Field(
        default=None, serialization_alias="additional_attributes"
    )
    created_at: datetime


class RiskDriverBreakdownSchema(BaseSchema):
    """Granular weight allocation and score description for a risk score driver."""

    driver_name: str
    driver_value: Optional[str] = None
    driver_weight: Optional[float] = None
    contribution_score: Optional[float] = None
    explanation: Optional[str] = None


class RiskAssessmentResponse(UUIDModel):
    """Credit risk rating output profile."""

    dataset_id: uuid.UUID
    version_id: Optional[uuid.UUID] = None
    borrower_id: Optional[uuid.UUID] = None
    loan_id: Optional[uuid.UUID] = None
    risk_score: float
    risk_category: RiskCategoryEnum
    risk_driver_summary: Optional[str] = None
    assessment_version: int
    rule_set_version: Optional[str] = None
    created_at: datetime
    driver_breakdowns: Optional[List[RiskDriverBreakdownSchema]] = None


class PortfolioSnapshotResponse(UUIDModel):
    """Overall portfolio financial metrics profile."""

    dataset_id: uuid.UUID
    version_id: Optional[uuid.UUID] = None
    portfolio_value: Optional[float] = None
    total_loans: Optional[int] = None
    total_borrowers: Optional[int] = None
    outstanding_exposure: Optional[float] = None
    high_risk_exposure: Optional[float] = None
    average_risk_score: Optional[float] = None
    average_loan_size: Optional[float] = None
    concentration_index: Optional[float] = None
    diversification_index: Optional[float] = None
    snapshot_date: Optional[date] = None
    created_at: datetime


class PortfolioSegmentMetricResponse(UUIDModel):
    """Portfolio slicing metric dimensions (e.g. by region or purpose)."""

    dataset_id: uuid.UUID
    version_id: Optional[uuid.UUID] = None
    segment_type: str
    segment_value: str
    borrower_count: Optional[int] = None
    loan_count: Optional[int] = None
    portfolio_value: Optional[float] = None
    outstanding_exposure: Optional[float] = None
    average_risk_score: Optional[float] = None
    high_risk_count: Optional[int] = None
    high_risk_exposure: Optional[float] = None
    created_at: datetime


class ConcentrationMetricResponse(UUIDModel):
    """HHI concentration ranking values."""

    dataset_id: uuid.UUID
    version_id: Optional[uuid.UUID] = None
    concentration_type: str
    concentration_key: str
    exposure_amount: Optional[float] = None
    exposure_percentage: Optional[float] = None
    rank: Optional[int] = None
    created_at: datetime


class TrendMetricResponse(UUIDModel):
    """Time-series value track metrics."""

    dataset_id: uuid.UUID
    version_id: Optional[uuid.UUID] = None
    metric_name: str
    period_type: str
    period_value: str
    metric_value: Optional[float] = None
    dimension_name: Optional[str] = None
    dimension_value: Optional[str] = None
    created_at: datetime


class RiskMigrationCellResponse(UUIDModel):
    """Risk rating transition details."""

    dataset_id: uuid.UUID
    version_id: Optional[uuid.UUID] = None
    from_risk_category: RiskCategoryEnum
    to_risk_category: RiskCategoryEnum
    borrower_count: Optional[int] = None
    exposure_amount: Optional[float] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    created_at: datetime


class DataQualityAnalyticsResponse(BaseSchema):
    """Data quality overview statistics."""

    dataset_id: uuid.UUID
    validation_score: Optional[float] = None
    total_records: int
    valid_records: int
    invalid_records: int
    missing_fields_count: int
    duplicate_records_count: int


class DiagnosticAnalyticsResponse(BaseSchema):
    """Analytical issues diagnostic indicators."""

    dataset_id: uuid.UUID
    critical_errors_count: int
    anomalies_detected: int
    unmapped_columns_count: int
    inconsistencies_flagged: int


class VintageAnalysisCellSchema(BaseSchema):
    """Cohorted vintage default performance metric tracker."""

    cohort_period: str = Field(description="Format: YYYY-MM or YYYY-Q#")
    months_on_book: int = Field(description="Age tracking in months")
    active_balance: float
    default_balance: float
    default_rate: float
