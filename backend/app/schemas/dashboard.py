from typing import Any, Dict, List

from pydantic import BaseModel, Field

from app.schemas.common import BaseSchema


class AdminDashboardMetricSchema(BaseModel):
    """General admin system statistics profile."""

    total_users_count: int
    active_users_count: int
    total_datasets_uploaded: int
    storage_used_bytes: int
    system_load_status: str = Field(description="Operational status descriptor (e.g. HEALTHY)")


class AdminDashboardResponse(BaseSchema):
    """Aggregate payload returned for the admin platform status dashboard."""

    system_metrics: AdminDashboardMetricSchema
    recent_activity_logs: List[Dict[str, Any]] = Field(default_factory=list)


class RiskDistributionSchema(BaseModel):
    """Bucket count mapping for risk category distribution."""

    low_risk_count: int
    medium_risk_count: int
    high_risk_count: int
    low_risk_exposure: float
    medium_risk_exposure: float
    high_risk_exposure: float


class RiskDashboardResponse(BaseSchema):
    """Comprehensive portfolio aggregate statistics payload."""

    total_portfolio_exposure: float
    weighted_average_risk_score: float
    total_delinquency_exposure: float
    delinquent_loans_count: int
    risk_distribution: RiskDistributionSchema
    recent_risk_trends: List[Dict[str, Any]] = Field(default_factory=list, description="Historical trend list")
    sector_concentration: List[Dict[str, Any]] = Field(
        default_factory=list, description="Top exposure key-value objects"
    )
