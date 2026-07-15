"""
Schema inferer — infers column data types and candidate canonical field matches.

Uses a comprehensive alias dictionary mapping common dataset headers
(including Home Credit, Kaggle, and generic banking column names) to
RiskLens canonical fields with confidence scores.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pandas as pd

from app.utils.strings import normalize_column_name

logger = logging.getLogger(__name__)


@dataclass
class InferredColumn:
    """Result of schema inference for a single column."""

    original_name: str
    normalized_name: str
    inferred_dtype: str  # "integer", "float", "string", "boolean", "datetime"
    candidate_canonical_field: Optional[str] = None
    confidence: float = 0.0
    sample_values: List[Any] = field(default_factory=list)


# ── Canonical field definitions ──────────────────────────────────────────────
# Required canonical fields
REQUIRED_CANONICAL_FIELDS = frozenset(
    {
        "borrower_id",
        "income",
        "employment_type",
        "loan_amount",
    }
)

# Strongly recommended canonical fields
RECOMMENDED_CANONICAL_FIELDS = frozenset(
    {
        "age",
        "gender",
        "education_level",
        "marital_status",
        "occupation",
        "region",
        "loan_term",
        "interest_rate",
        "outstanding_amount",
        "annuity_amount",
        "repayment_status",
        "delinquency_days",
        "disbursement_date",
        "loan_status",
        "historical_default_flag",
        "regional_risk_indicator",
        "housing_type",
        "family_size",
        "credit_burden",
        "asset_value",
    }
)

ALL_CANONICAL_FIELDS = REQUIRED_CANONICAL_FIELDS | RECOMMENDED_CANONICAL_FIELDS

# ── Alias dictionary ────────────────────────────────────────────────────────
# Maps normalized column names → (canonical_field, confidence).
# Confidence 1.0 = exact known alias; 0.85 = high-likelihood heuristic.
_ALIAS_MAP: Dict[str, tuple[str, float]] = {
    # ── borrower_id ──
    "sk_id_curr": ("borrower_id", 1.0),
    "borrower_id": ("borrower_id", 1.0),
    "customer_id": ("borrower_id", 0.95),
    "client_id": ("borrower_id", 0.95),
    "id": ("borrower_id", 0.5),
    "applicant_id": ("borrower_id", 0.9),
    # ── income ──
    "amt_income_total": ("income", 1.0),
    "annual_income": ("income", 1.0),
    "customerincome": ("income", 0.95),
    "income": ("income", 1.0),
    "yearly_income": ("income", 0.95),
    "monthly_income": ("income", 0.9),
    "applicantincome": ("income", 0.95),
    "coapplicantincome": ("income", 0.6),
    # ── employment_type ──
    "name_income_type": ("employment_type", 1.0),
    "employment_type": ("employment_type", 1.0),
    "employment": ("employment_type", 0.9),
    "job_type": ("employment_type", 0.85),
    "self_employed": ("employment_type", 0.7),
    # ── loan_amount ──
    "amt_credit": ("loan_amount", 1.0),
    "requested_loan": ("loan_amount", 0.95),
    "loan_amount": ("loan_amount", 1.0),
    "loanamount": ("loan_amount", 1.0),
    "credit_amount": ("loan_amount", 0.95),
    "amt_goods_price": ("loan_amount", 0.7),
    # ── loan_purpose ──
    "loan_purpose": ("loan_purpose", 1.0),
    "purpose": ("loan_purpose", 0.9),
    "name_contract_type": ("loan_purpose", 0.8),
    # ── age ──
    "days_birth": ("age", 1.0),
    "age": ("age", 1.0),
    "applicant_age": ("age", 0.95),
    "borrower_age": ("age", 0.95),
    # ── gender ──
    "code_gender": ("gender", 1.0),
    "gender": ("gender", 1.0),
    "sex": ("gender", 0.95),
    # ── education_level ──
    "name_education_type": ("education_level", 1.0),
    "education": ("education_level", 0.95),
    "education_level": ("education_level", 1.0),
    # ── marital_status ──
    "name_family_status": ("marital_status", 1.0),
    "marital_status": ("marital_status", 1.0),
    "married": ("marital_status", 0.85),
    # ── occupation ──
    "occupation_type": ("occupation", 1.0),
    "occupation": ("occupation", 1.0),
    "job_title": ("occupation", 0.85),
    # ── region ──
    "region": ("region", 1.0),
    "reg_region_not_work_region": ("region", 0.5),
    "region_rating_client": ("regional_risk_indicator", 0.85),
    # ── loan_term ──
    "loan_term": ("loan_term", 1.0),
    "term": ("loan_term", 0.85),
    "loan_term_months": ("loan_term", 0.95),
    # ── interest_rate ──
    "interest_rate": ("interest_rate", 1.0),
    "rate": ("interest_rate", 0.7),
    "int_rate": ("interest_rate", 0.9),
    # ── outstanding_amount ──
    "outstanding_amount": ("outstanding_amount", 1.0),
    "balance": ("outstanding_amount", 0.7),
    "amt_balance": ("outstanding_amount", 0.85),
    # ── annuity_amount ──
    "amt_annuity": ("annuity_amount", 1.0),
    "annuity_amount": ("annuity_amount", 1.0),
    "annuity": ("annuity_amount", 0.9),
    # ── repayment_status ──
    "repayment_status": ("repayment_status", 1.0),
    "status": ("repayment_status", 0.5),
    # ── delinquency_days ──
    "delinquency_days": ("delinquency_days", 1.0),
    "days_delinquent": ("delinquency_days", 0.95),
    # ── disbursement_date ──
    "disbursement_date": ("disbursement_date", 1.0),
    "loan_date": ("disbursement_date", 0.85),
    # ── loan_status ──
    "loan_status": ("loan_status", 1.0),
    "name_contract_status": ("loan_status", 0.9),
    # ── historical_default_flag ──
    "target": ("historical_default_flag", 1.0),
    "default": ("historical_default_flag", 0.9),
    "historical_default_flag": ("historical_default_flag", 1.0),
    "defaulted": ("historical_default_flag", 0.9),
    # ── regional_risk_indicator ──
    "regional_risk_indicator": ("regional_risk_indicator", 1.0),
    "region_rating_client_w_city": ("regional_risk_indicator", 0.85),
    # ── housing_type ──
    "name_housing_type": ("housing_type", 1.0),
    "housing_type": ("housing_type", 1.0),
    "property_area": ("housing_type", 0.7),
    # ── family_size ──
    "cnt_children": ("family_size", 0.85),
    "family_size": ("family_size", 1.0),
    "cnt_fam_members": ("family_size", 0.9),
    "dependents": ("family_size", 0.8),
    # ── credit_burden ──
    "credit_burden": ("credit_burden", 1.0),
    "debt_to_income": ("credit_burden", 0.9),
    "dti": ("credit_burden", 0.85),
    # ── asset_value ──
    "asset_value": ("asset_value", 1.0),
    "total_assets": ("asset_value", 0.9),
    # ── employment_stability (special transform from DAYS_EMPLOYED) ──
    "days_employed": ("employment_stability", 0.9),
}


def _infer_pandas_dtype(series: pd.Series) -> str:
    """Map a pandas Series dtype to a human-readable type label."""
    dtype_str = str(series.dtype)
    if "int" in dtype_str:
        return "integer"
    if "float" in dtype_str:
        return "float"
    if "bool" in dtype_str:
        return "boolean"
    if "datetime" in dtype_str:
        return "datetime"
    return "string"


def _sample_values(series: pd.Series, n: int = 5) -> List[Any]:
    """Return up to *n* non-null unique sample values from a Series."""
    non_null = series.dropna()
    if non_null.empty:
        return []
    uniques = non_null.unique()
    samples = uniques[:n].tolist()
    # Ensure JSON-serialisable
    cleaned: List[Any] = []
    for v in samples:
        try:
            if hasattr(v, "item"):
                cleaned.append(v.item())
            else:
                cleaned.append(v)
        except Exception:
            cleaned.append(str(v))
    return cleaned


def infer_schema(df: pd.DataFrame) -> List[InferredColumn]:
    """
    Analyse a DataFrame and return inference results for every column.

    For each column:
    1. Infer data type from pandas dtype.
    2. Normalise the column header and look up the alias map.
    3. Collect sample values for UI preview.

    Parameters
    ----------
    df : pd.DataFrame
        The parsed tabular data.

    Returns
    -------
    list[InferredColumn]
        One entry per column, ordered by DataFrame column order.
    """
    results: List[InferredColumn] = []

    for col_name in df.columns:
        series = df[col_name]
        normalized = normalize_column_name(str(col_name))
        dtype_label = _infer_pandas_dtype(series)
        samples = _sample_values(series)

        candidate: Optional[str] = None
        confidence = 0.0

        # Exact alias lookup
        if normalized in _ALIAS_MAP:
            candidate, confidence = _ALIAS_MAP[normalized]
        else:
            # Substring / partial match fallback
            for alias_key, (canon, conf) in _ALIAS_MAP.items():
                if len(alias_key) >= 4 and alias_key in normalized:
                    candidate = canon
                    confidence = conf * 0.8  # penalise partial
                    break

        results.append(
            InferredColumn(
                original_name=str(col_name),
                normalized_name=normalized,
                inferred_dtype=dtype_label,
                candidate_canonical_field=candidate,
                confidence=confidence,
                sample_values=samples,
            )
        )

    logger.info(
        "Schema inference complete: %d columns, %d mapped candidates",
        len(results),
        sum(1 for r in results if r.candidate_canonical_field),
    )
    return results
