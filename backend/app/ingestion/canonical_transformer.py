"""
Canonical transformer — maps raw DataFrame rows to the RiskLens canonical
data model and populates Borrower / Loan tables.

This is the final stage of the ingestion pipeline. It:
1. Reads confirmed SchemaMapping rules for a dataset.
2. Iterates the DataFrame, producing ``canonical_data_json`` on each RawRecord.
3. Groups rows by ``borrower_id`` to create ``Borrower`` records.
4. Creates one ``Loan`` record per row.
"""

import logging
import math
import uuid
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.borrower import Borrower
from app.models.loan import Loan
from app.models.raw_record import RawRecord
from app.repositories.schema_mapping_repository import SchemaMappingRepository

logger = logging.getLogger(__name__)

# Borrower-level canonical fields (populated on Borrower model)
_BORROWER_FIELDS = {
    "borrower_id",
    "age",
    "gender",
    "income",
    "employment_type",
    "education_level",
    "marital_status",
    "region",
    "occupation",
    "housing_type",
    "family_size",
}

# Loan-level canonical fields (populated on Loan model)
_LOAN_FIELDS = {
    "loan_amount",
    "loan_purpose",
    "interest_rate",
    "loan_term",
    "loan_status",
    "disbursement_date",
    "outstanding_amount",
    "annuity_amount",
    "delinquency_days",
    "historical_default_flag",
    "asset_value",
    "credit_burden",
    "repayment_status",
    "date_is_synthetic",
    "additional_attributes_json",
}


def _safe_float(v: Any) -> Optional[float]:
    """Convert a value to float, returning None on failure or NaN."""
    if v is None:
        return None
    try:
        f = float(v)
        return None if math.isnan(f) else f
    except (ValueError, TypeError):
        return None


def _safe_int(v: Any) -> Optional[int]:
    """Convert a value to int, returning None on failure."""
    if v is None:
        return None
    try:
        f = float(v)
        if math.isnan(f):
            return None
        return int(f)
    except (ValueError, TypeError):
        return None


def _safe_str(v: Any) -> Optional[str]:
    """Convert a value to string, returning None for empty/nan."""
    if v is None:
        return None
    s = str(v).strip()
    if s.lower() in ("nan", "none", "null", ""):
        return None
    return s


def _safe_bool(v: Any) -> Optional[bool]:
    """Convert to bool. Treats 1/0, True/False, 'yes'/'no'."""
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    if s in ("1", "true", "yes", "y"):
        return True
    if s in ("0", "false", "no", "n"):
        return False
    return None


def _safe_date(v: Any) -> Optional[date]:
    """Try to parse a date value."""
    if v is None:
        return None
    if isinstance(v, (datetime, date)):
        return v if isinstance(v, date) else v.date()
    s = str(v).strip()
    if s.lower() in ("nan", "none", "nat", ""):
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y%m%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _normalize_loan_purpose(val: Any) -> str:
    """Normalize raw loan purpose values into canonical categories."""
    import re
    if val is None:
        return "Other/Unclassified"
    
    s = str(val).strip().lower()
    if s in ("", "nan", "none", "null", "n/a", "na"):
        return "Other/Unclassified"
    
    # 1. Check exact match first
    if s in ("debt consolidation", "debt_consolidation", "debt-consolidation", "consolidation", "debt", "refinance", "refinancing", "credit card", "credit-card", "credit_card"):
        return "Debt consolidation"
    
    if s in ("home improvement", "home_improvement", "home-improvement", "renovation", "remodel", "repair", "repairs", "maintenance", "home"):
        return "Home improvement"
        
    if s in ("education", "school", "college", "university", "study", "student", "tuition", "academic"):
        return "Education"
        
    if s in ("business", "small business", "small_business", "small-business", "startup", "start-up", "start_up", "commercial", "trade", "office", "venture"):
        return "Business"
        
    if s in ("auto", "car", "automobile", "vehicle", "motorcycle"):
        return "Auto"
        
    if s in ("medical", "health", "healthcare", "hospital", "treatment", "clinical", "surgery", "dental"):
        return "Medical"

    # 2. Fallback to word token matching to avoid substring collisions (e.g. "healthcare" containing "car")
    words = set(re.findall(r'[a-z0-9]+', s))
    
    if any(w in words for w in ("consolidation", "debt", "refinance", "refinancing", "card")):
        return "Debt consolidation"
        
    if any(w in words for w in ("improvement", "renovation", "renovations", "remodel", "remodeling", "repair", "repairs", "maintenance", "home")):
        return "Home improvement"
        
    if any(w in words for w in ("education", "educational", "school", "college", "university", "study", "studies", "student", "tuition", "academic")):
        return "Education"
        
    if any(w in words for w in ("business", "startup", "startups", "commercial", "trade", "office", "venture")):
        return "Business"
        
    if any(w in words for w in ("auto", "car", "cars", "automobile", "automobiles", "vehicle", "vehicles", "motorcycle", "motorcycles")):
        return "Auto"
        
    if any(w in words for w in ("medical", "health", "healthcare", "hospital", "hospitals", "treatment", "treatments", "clinical", "surgery", "dental")):
        return "Medical"
        
    return "Other/Unclassified"


def _transform_special_fields(canonical: Dict[str, Any]) -> Dict[str, Any]:
    """Apply domain-specific transformations (e.g. DAYS_BIRTH → age)."""
    # DAYS_BIRTH is negative days from today; convert to positive years
    if "age" in canonical and canonical["age"] is not None:
        age_val = _safe_float(canonical["age"])
        if age_val is not None and age_val < 0:
            canonical["age"] = int(abs(age_val) / 365.25)

    # DAYS_EMPLOYED — convert to employment_stability in years
    if "employment_stability" in canonical:
        emp_val = _safe_float(canonical.get("employment_stability"))
        if emp_val is not None:
            # Negative = employed; 365243 = unemployed sentinel in Home Credit
            if emp_val == 365243:
                canonical.setdefault("employment_type", "Unemployed")
            elif emp_val < 0:
                years = round(abs(emp_val) / 365.25, 1)
                canonical["employment_years"] = years

    # Normalize loan_purpose
    canonical["loan_purpose"] = _normalize_loan_purpose(canonical.get("loan_purpose"))

    return canonical


def _build_canonical_dict(
    row_dict: Dict[str, Any],
    mapping_lookup: Dict[str, str],
) -> Dict[str, Any]:
    """
    Apply the mapping_lookup to translate raw column names to canonical field names.

    Parameters
    ----------
    row_dict : dict
        One row of raw data (keys = original column names).
    mapping_lookup : dict
        ``{original_column_name: canonical_field}``.

    Returns
    -------
    dict
        Canonical key→value pairs.
    """
    canonical: Dict[str, Any] = {}
    for orig_col, value in row_dict.items():
        if orig_col in mapping_lookup:
            canonical_key = mapping_lookup[orig_col]
            canonical[canonical_key] = value

    return _transform_special_fields(canonical)


async def transform_and_populate(
    db: AsyncSession,
    dataset_id: uuid.UUID,
    version_id: uuid.UUID,
    df: pd.DataFrame,
) -> Tuple[int, int, int]:
    """
    Run the canonical transformation for a full DataFrame.

    1. Load confirmed ``SchemaMapping`` rules from the database.
    2. For each row: create a ``RawRecord`` with ``canonical_data_json``.
    3. Group by ``borrower_id`` to create ``Borrower`` rows.
    4. Create one ``Loan`` per row.

    Returns
    -------
    tuple[int, int, int]
        ``(raw_records_count, borrowers_count, loans_count)``
    """
    # 1. Load mappings
    mapping_repo = SchemaMappingRepository(db)
    mappings = await mapping_repo.get_by_dataset(dataset_id, version_id)

    if not mappings:
        logger.warning("No schema mappings found for dataset %s — skipping transformation.", dataset_id)
        return 0, 0, 0

    from sqlalchemy import select
    from app.models.dataset_column import DatasetColumn
    from app.utils.strings import normalize_column_name

    # 1.1 Load DatasetColumn metadata to identify profiled date-like columns
    col_stmt = select(DatasetColumn).where(
        DatasetColumn.dataset_id == dataset_id,
        DatasetColumn.version_id == version_id
    )
    col_res = await db.execute(col_stmt)
    dataset_cols = col_res.scalars().all()

    profiled_date_cols = {
        col.original_column_name
        for col in dataset_cols
        if col.inferred_data_type == "datetime" or col.mapped_data_type == "datetime"
    }

    # 1.2 Build priority chain of candidate date columns
    # Step 1: Genuine disbursement date columns (mapped to disbursement_date)
    disb_cols = [m.original_column_name for m in mappings if m.canonical_field == "disbursement_date"]

    # Step 2: Application date candidates (priority order of aliases)
    APP_DATE_ALIASES = [
        "application_date",
        "app_date",
        "applied_date",
        "applied_at",
        "date_applied",
        "application_dt",
        "applicationdate",
    ]
    app_date_cols = []
    for alias in APP_DATE_ALIASES:
        for col in df.columns:
            if normalize_column_name(str(col)) == alias:
                app_date_cols.append(col)

    # Step 3: First payment date candidates (priority order of aliases)
    PAY_DATE_ALIASES = [
        "first_payment_date",
        "first_pay_date",
        "first_repayment_date",
        "first_payment_dt",
        "firstpaymentdate",
    ]
    pay_date_cols = []
    for alias in PAY_DATE_ALIASES:
        for col in df.columns:
            if normalize_column_name(str(col)) == alias:
                pay_date_cols.append(col)

    # Step 4: Other profiled date columns (excluding any checked in steps 1, 2, 3), sorted alphabetically
    checked_cols = set(disb_cols) | set(app_date_cols) | set(pay_date_cols)
    other_date_cols = sorted(list(profiled_date_cols - checked_cols))

    # Form the deterministic sequence of column candidates to check
    fallback_cols = []
    for c in disb_cols:
        if c not in fallback_cols:
            fallback_cols.append(c)
    for c in app_date_cols:
        if c not in fallback_cols:
            fallback_cols.append(c)
    for c in pay_date_cols:
        if c not in fallback_cols:
            fallback_cols.append(c)
    for c in other_date_cols:
        if c not in fallback_cols:
            fallback_cols.append(c)

    logger.info("Deterministic canonical date fallback column priority: %s", fallback_cols)

    mapping_lookup: Dict[str, str] = {m.original_column_name: m.canonical_field for m in mappings}

    # 2. Build canonical rows and RawRecords
    borrower_map: Dict[str, Dict[str, Any]] = {}  # source_borrower_id → borrower attrs
    loan_rows: List[Tuple[Dict[str, Any], Optional[str]]] = []  # (canonical, source_borrower_id)
    raw_count = 0

    for row_idx, row in df.iterrows():
        row_dict = {}
        for col in df.columns:
            val = row[col]
            # Ensure JSON-serialisable
            if pd.isna(val):
                row_dict[str(col)] = None
            elif hasattr(val, "item"):
                row_dict[str(col)] = val.item()
            else:
                row_dict[str(col)] = val

        canonical = _build_canonical_dict(row_dict, mapping_lookup)

        # Determine canonical date using the fallback sequence
        sourced_date = None
        date_is_synthetic = False

        for col in fallback_cols:
            val = row_dict.get(col)
            parsed = _safe_date(val)
            if parsed is not None:
                sourced_date = parsed
                break

        if sourced_date is None:
            date_is_synthetic = True

        # Update canonical with the sourced date and the synthetic flag
        canonical["disbursement_date"] = sourced_date.isoformat() if sourced_date is not None else None
        canonical["date_is_synthetic"] = date_is_synthetic

        # Create RawRecord
        rr = RawRecord(
            id=uuid.uuid4(),
            dataset_id=dataset_id,
            version_id=version_id,
            source_row_number=int(row_idx) + 1,
            raw_data_json=row_dict,
            canonical_data_json=canonical if canonical else None,
        )
        db.add(rr)
        raw_count += 1

        # Collect borrower info
        borrower_id_val = _safe_str(canonical.get("borrower_id"))
        if borrower_id_val:
            if borrower_id_val not in borrower_map:
                borrower_attrs = {}
                for field_name in _BORROWER_FIELDS:
                    if field_name in canonical and field_name != "borrower_id":
                        borrower_attrs[field_name] = canonical[field_name]
                borrower_map[borrower_id_val] = borrower_attrs

        # Collect loan info
        loan_attrs = {}
        for field_name in _LOAN_FIELDS:
            if field_name in canonical:
                loan_attrs[field_name] = canonical[field_name]
        loan_rows.append((loan_attrs, borrower_id_val))

        # Flush in batches of 500 to avoid memory pressure
        if raw_count % 500 == 0:
            await db.flush()

    await db.flush()

    # 3. Create Borrower records
    borrower_db_map: Dict[str, uuid.UUID] = {}
    for source_bid, attrs in borrower_map.items():
        borrower = Borrower(
            id=uuid.uuid4(),
            dataset_id=dataset_id,
            version_id=version_id,
            source_borrower_id=source_bid,
            age=_safe_int(attrs.get("age")),
            gender=_safe_str(attrs.get("gender")),
            income=_safe_float(attrs.get("income")),
            employment_type=_safe_str(attrs.get("employment_type")),
            education_level=_safe_str(attrs.get("education_level")),
            marital_status=_safe_str(attrs.get("marital_status")),
            region=_safe_str(attrs.get("region")),
            occupation=_safe_str(attrs.get("occupation")),
            housing_type=_safe_str(attrs.get("housing_type")),
            family_size=_safe_int(attrs.get("family_size")),
        )
        db.add(borrower)
        borrower_db_map[source_bid] = borrower.id

    await db.flush()
    borrower_count = len(borrower_db_map)

    # 4. Create Loan records
    loan_count = 0
    for loan_attrs, source_bid in loan_rows:
        if not loan_attrs:
            continue

        additional_attrs = loan_attrs.get("additional_attributes_json") or {}
        if not isinstance(additional_attrs, dict):
            additional_attrs = {}

        if "date_is_synthetic" in loan_attrs:
            additional_attrs["date_is_synthetic"] = loan_attrs["date_is_synthetic"]

        loan = Loan(
            id=uuid.uuid4(),
            dataset_id=dataset_id,
            version_id=version_id,
            borrower_id=borrower_db_map.get(source_bid) if source_bid else None,
            loan_amount=_safe_float(loan_attrs.get("loan_amount")),
            loan_purpose=_safe_str(loan_attrs.get("loan_purpose")),
            interest_rate=_safe_float(loan_attrs.get("interest_rate")),
            loan_term=_safe_int(loan_attrs.get("loan_term")),
            loan_status=_safe_str(loan_attrs.get("loan_status")),
            disbursement_date=_safe_date(loan_attrs.get("disbursement_date")),
            outstanding_amount=_safe_float(loan_attrs.get("outstanding_amount")),
            annuity_amount=_safe_float(loan_attrs.get("annuity_amount")),
            delinquency_days=_safe_int(loan_attrs.get("delinquency_days")),
            historical_default_flag=_safe_bool(loan_attrs.get("historical_default_flag")),
            asset_value=_safe_float(loan_attrs.get("asset_value")),
            repayment_burden_ratio=_safe_float(loan_attrs.get("credit_burden")),
            additional_attributes_json=additional_attrs if additional_attrs else None,
        )
        db.add(loan)
        loan_count += 1

        if loan_count % 500 == 0:
            await db.flush()

    await db.flush()

    logger.info(
        "Canonical transformation complete for dataset %s: " "%d raw records, %d borrowers, %d loans",
        dataset_id,
        raw_count,
        borrower_count,
        loan_count,
    )
    return raw_count, borrower_count, loan_count
