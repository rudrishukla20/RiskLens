from typing import Any, Optional

from pydantic import BaseModel


class DataQualityAnalyticsResponse(BaseModel):
    total_records: Optional[Any] = None
    valid_records: Optional[Any] = None
    invalid_records: Optional[Any] = None
    missing_value_count: Optional[Any] = None
    missing_value_percentage: Optional[Any] = None
    duplicate_count: Optional[Any] = None
    duplicate_percentage: Optional[Any] = None
    invalid_datatype_count: Optional[Any] = None
    invalid_business_rule_count: Optional[Any] = None
    outlier_count: Optional[Any] = None
    completeness_score: Optional[Any] = None
    uniqueness_score: Optional[Any] = None
    validity_score: Optional[Any] = None
    consistency_score: Optional[Any] = None
    dataset_health_score: Optional[Any] = None
    schema_drift_indicator: Optional[Any] = None
    validation_trend_by_dataset_version: Optional[Any] = None
    validation_trend: Optional[Any] = None
    visualizations: Optional[Any] = None


class DatasetProfilingResponse(BaseModel):
    rows: Optional[Any] = None
    columns: Optional[Any] = None
    data_types: Optional[Any] = None
    numeric_statistics: Optional[Any] = None
    categorical_distributions: Optional[Any] = None
    percentiles: Optional[Any] = None
    outlier_summary: Optional[Any] = None
    skewness: Optional[Any] = None
    kurtosis: Optional[Any] = None
    correlation_matrix: Optional[Any] = None
    column_health_cards: Optional[Any] = None
    visualizations: Optional[Any] = None


class BorrowerAnalyticsEngineResponse(BaseModel):
    borrower_count: Optional[Any] = None
    income_distribution: Optional[Any] = None
    income_bands: Optional[Any] = None
    age_bands: Optional[Any] = None
    employment_distribution: Optional[Any] = None
    occupation_distribution: Optional[Any] = None
    education_distribution: Optional[Any] = None
    marital_distribution: Optional[Any] = None
    region_distribution: Optional[Any] = None
    family_size_distribution: Optional[Any] = None
    risk_by_borrower_segment: Optional[Any] = None
    exposure_by_borrower_segment: Optional[Any] = None
    visualizations: Optional[Any] = None


class LoanAnalyticsEngineResponse(BaseModel):
    loan_count: Optional[Any] = None
    loan_amount_distribution: Optional[Any] = None
    exposure_metrics: Optional[Any] = None
    interest_rate_stats: Optional[Any] = None
    term_distribution: Optional[Any] = None
    annuity_stats: Optional[Any] = None
    delinquency_buckets: Optional[Any] = None
    status_distribution: Optional[Any] = None
    purpose_distribution: Optional[Any] = None
    repayment_burden_ratio: Optional[Any] = None
    visualizations: Optional[Any] = None
