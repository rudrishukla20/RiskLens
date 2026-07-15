import logging
import uuid
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums.validation_status import ValidationStatusEnum
from app.ingestion.schema_inferer import REQUIRED_CANONICAL_FIELDS
from app.models.dataset import Dataset
from app.models.dataset_version import DatasetVersion
from app.models.raw_record import RawRecord
from app.models.schema_mapping import SchemaMapping
from app.models.validation import ValidationRun
from app.models.validation_issue import ValidationIssue
from app.utils.statistics import calculate_iqr_bounds, calculate_median

logger = logging.getLogger(__name__)


class DataQualityEngine:
    """
    Banking-grade Data Quality Engine.
    Executes profile rules validation, outlier checkings, missing field detection,
    and type conversions validation on RawRecords canonical JSON payloads.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def run_validation(
        self, dataset_id: uuid.UUID, version_id: uuid.UUID, user_id: Optional[uuid.UUID] = None
    ) -> ValidationRun:
        """
        Runs validation checks on all raw records.
        """
        logger.info("Starting data quality validation run for dataset_id=%s, version_id=%s", dataset_id, version_id)

        # 1. Fetch ValidationRun (if any exists in PENDING/VALIDATING) or create a new one
        # Let's create a new active run
        run = ValidationRun(
            id=uuid.uuid4(),
            dataset_id=dataset_id,
            version_id=version_id,
            status=ValidationStatusEnum.VALIDATING,
            started_at=datetime.now(timezone.utc),
            created_by=user_id,
        )
        self.db.add(run)
        await self.db.flush()

        # Update dataset validation status
        dataset_stmt = select(Dataset).where(Dataset.id == dataset_id)
        dataset_res = await self.db.execute(dataset_stmt)
        dataset = dataset_res.scalar_one_or_none()
        if dataset:
            dataset.validation_status = ValidationStatusEnum.VALIDATING
            self.db.add(dataset)

        # 2. Fetch SchemaMappings
        mapping_stmt = select(SchemaMapping).where(
            SchemaMapping.dataset_id == dataset_id, SchemaMapping.version_id == version_id
        )
        mapping_res = await self.db.execute(mapping_stmt)
        mappings = mapping_res.scalars().all()

        # Maps original column names -> canonical fields
        mapping_lookup = {m.original_column_name: m.canonical_field for m in mappings}
        # Reverse lookup: canonical field -> original column
        reverse_lookup = {m.canonical_field: m.original_column_name for m in mappings}

        # 3. Fetch RawRecords
        records_stmt = (
            select(RawRecord)
            .where(RawRecord.dataset_id == dataset_id, RawRecord.version_id == version_id)
            .order_by(RawRecord.source_row_number.asc())
        )

        records_res = await self.db.execute(records_stmt)
        records = records_res.scalars().all()

        total_records = len(records)
        if total_records == 0:
            run.status = ValidationStatusEnum.PASSED
            run.total_records = 0
            run.validation_score = 100.0
            run.completed_at = datetime.now(timezone.utc)
            if dataset:
                dataset.validation_status = ValidationStatusEnum.PASSED
            await self.db.flush()
            return run

        # Counts trackers
        missing_count = 0
        duplicate_count = 0
        type_error_count = 0
        outlier_count = 0
        rule_violation_count = 0
        invalid_records = 0
        valid_records = 0

        # Unique checks tracking
        seen_borrowers = set()
        seen_loans = set()

        issues_to_create: List[ValidationIssue] = []

        # 4. Perform checks per record
        for record in records:
            raw_data = record.raw_data_json or {}
            canonical_data = record.canonical_data_json or {}
            row_num = record.source_row_number
            record_has_error = False

            # A. Check missing values for required fields
            for req_field in REQUIRED_CANONICAL_FIELDS:
                is_critical = req_field in ("borrower_id", "income", "loan_amount")
                severity = "ERROR" if is_critical else "WARNING"

                orig_col = reverse_lookup.get(req_field)
                if not orig_col:
                    # Required field is not mapped at all
                    if is_critical:
                        record_has_error = True
                    missing_count += 1
                    issues_to_create.append(
                        ValidationIssue(
                            id=uuid.uuid4(),
                            validation_run_id=run.id,
                            dataset_id=dataset_id,
                            source_row_number=row_num,
                            column_name=None,
                            issue_type="MISSING_VALUE",
                            severity=severity,
                            message=f"Required canonical field '{req_field}' is not mapped to any column in the dataset.",
                            observed_value=None,
                        )
                    )
                    continue

                raw_val = raw_data.get(orig_col)
                if raw_val is None or str(raw_val).strip() == "" or str(raw_val).lower() in ("nan", "none", "null"):
                    if is_critical:
                        record_has_error = True
                    missing_count += 1
                    issues_to_create.append(
                        ValidationIssue(
                            id=uuid.uuid4(),
                            validation_run_id=run.id,
                            dataset_id=dataset_id,
                            source_row_number=row_num,
                            column_name=orig_col,
                            issue_type="MISSING_VALUE",
                            severity=severity,
                            message=f"Missing value for required canonical field '{req_field}' (mapped from column '{orig_col}').",
                            observed_value=str(raw_val) if raw_val is not None else None,
                        )
                    )

            # B. Check fields conversions and other canonical constraints
            for orig_col, canon_field in mapping_lookup.items():
                raw_val = raw_data.get(orig_col)
                canon_val = canonical_data.get(canon_field)

                # Skip checking if raw value is completely empty
                if raw_val is None or str(raw_val).strip() == "" or str(raw_val).lower() in ("nan", "none", "null"):
                    continue

                # Type mismatch check: raw value was present, but canonical value failed to parse
                if canon_val is None:
                    is_critical = canon_field in ("borrower_id", "income", "loan_amount")
                    if is_critical:
                        record_has_error = True
                    type_error_count += 1
                    issues_to_create.append(
                        ValidationIssue(
                            id=uuid.uuid4(),
                            validation_run_id=run.id,
                            dataset_id=dataset_id,
                            source_row_number=row_num,
                            column_name=orig_col,
                            issue_type="INVALID_TYPE",
                            severity="ERROR" if is_critical else "WARNING",
                            message=f"Failed to parse column '{orig_col}' to canonical type '{canon_field}'.",
                            observed_value=str(raw_val),
                        )
                    )
                    continue

                # Outlier checks
                if canon_field == "age":
                    if not (18 <= canon_val <= 120):
                        outlier_count += 1
                        issues_to_create.append(
                            ValidationIssue(
                                id=uuid.uuid4(),
                                validation_run_id=run.id,
                                dataset_id=dataset_id,
                                source_row_number=row_num,
                                column_name=orig_col,
                                issue_type="OUTLIER",
                                severity="WARNING",
                                message=f"Age '{canon_val}' is outside reasonable banking limits (18-120).",
                                observed_value=str(raw_val),
                            )
                        )

                elif canon_field == "income":
                    if canon_val < 0:
                        record_has_error = True
                        outlier_count += 1
                        issues_to_create.append(
                            ValidationIssue(
                                id=uuid.uuid4(),
                                validation_run_id=run.id,
                                dataset_id=dataset_id,
                                source_row_number=row_num,
                                column_name=orig_col,
                                issue_type="OUTLIER",
                                severity="ERROR",
                                message=f"Income '{canon_val}' cannot be negative.",
                                observed_value=str(raw_val),
                            )
                        )

                elif canon_field == "loan_amount":
                    if canon_val <= 0:
                        record_has_error = True
                        outlier_count += 1
                        issues_to_create.append(
                            ValidationIssue(
                                id=uuid.uuid4(),
                                validation_run_id=run.id,
                                dataset_id=dataset_id,
                                source_row_number=row_num,
                                column_name=orig_col,
                                issue_type="OUTLIER",
                                severity="ERROR",
                                message=f"Loan amount '{canon_val}' must be positive.",
                                observed_value=str(raw_val),
                            )
                        )

                elif canon_field == "interest_rate":
                    # Assume check bounds: rate should be positive. If rate is > 100.0 or < 0.0
                    if not (0.0 <= canon_val <= 100.0):
                        outlier_count += 1
                        issues_to_create.append(
                            ValidationIssue(
                                id=uuid.uuid4(),
                                validation_run_id=run.id,
                                dataset_id=dataset_id,
                                source_row_number=row_num,
                                column_name=orig_col,
                                issue_type="OUTLIER",
                                severity="WARNING",
                                message=f"Interest rate '{canon_val}' is outside standard range (0-100%).",
                                observed_value=str(raw_val),
                            )
                        )

                elif canon_field == "loan_term":
                    if not (1 <= canon_val <= 600):
                        outlier_count += 1
                        issues_to_create.append(
                            ValidationIssue(
                                id=uuid.uuid4(),
                                validation_run_id=run.id,
                                dataset_id=dataset_id,
                                source_row_number=row_num,
                                column_name=orig_col,
                                issue_type="OUTLIER",
                                severity="WARNING",
                                message=f"Loan term '{canon_val}' months is outside normal ranges.",
                                observed_value=str(raw_val),
                            )
                        )

                # Duplicate check: borrower_id
                if canon_field == "borrower_id":
                    b_id = str(canon_val).strip()
                    if b_id in seen_borrowers:
                        duplicate_count += 1
                        issues_to_create.append(
                            ValidationIssue(
                                id=uuid.uuid4(),
                                validation_run_id=run.id,
                                dataset_id=dataset_id,
                                source_row_number=row_num,
                                column_name=orig_col,
                                issue_type="DUPLICATE",
                                severity="INFO",
                                message=f"Duplicate borrower ID '{b_id}' found in row {row_num}.",
                                observed_value=str(raw_val),
                            )
                        )
                    seen_borrowers.add(b_id)

                # Duplicate check: loan_id
                if canon_field == "loan_id":
                    l_id = str(canon_val).strip()
                    if l_id in seen_loans:
                        duplicate_count += 1
                        issues_to_create.append(
                            ValidationIssue(
                                id=uuid.uuid4(),
                                validation_run_id=run.id,
                                dataset_id=dataset_id,
                                source_row_number=row_num,
                                column_name=orig_col,
                                issue_type="DUPLICATE",
                                severity="WARNING",
                                message=f"Duplicate loan ID '{l_id}' found in row {row_num}.",
                                observed_value=str(raw_val),
                            )
                        )
                    seen_loans.add(l_id)

            # C. Business rule dependencies check
            outstanding = canonical_data.get("outstanding_amount")
            loan_amt = canonical_data.get("loan_amount")
            if outstanding is not None and loan_amt is not None:
                if outstanding > loan_amt:
                    rule_violation_count += 1
                    issues_to_create.append(
                        ValidationIssue(
                            id=uuid.uuid4(),
                            validation_run_id=run.id,
                            dataset_id=dataset_id,
                            source_row_number=row_num,
                            column_name=reverse_lookup.get("outstanding_amount"),
                            issue_type="BUSINESS_RULE_VIOLATION",
                            severity="WARNING",
                            message=f"Outstanding exposure '{outstanding}' exceeds original loan amount '{loan_amt}'.",
                            observed_value=f"outstanding={outstanding}, loan_amt={loan_amt}",
                        )
                    )

            annuity = canonical_data.get("annuity_amount")
            income = canonical_data.get("income")
            if annuity is not None and income is not None and income > 0:
                annuity_to_income_ratio = annuity / income
                threshold = 0.4
                if annuity_to_income_ratio > threshold:
                    rule_violation_count += 1
                    issues_to_create.append(
                        ValidationIssue(
                            id=uuid.uuid4(),
                            validation_run_id=run.id,
                            dataset_id=dataset_id,
                            source_row_number=row_num,
                            column_name=reverse_lookup.get("annuity_amount"),
                            issue_type="BUSINESS_RULE_VIOLATION",
                            severity="WARNING",
                            message=f"Annuity-to-income ratio '{round(annuity_to_income_ratio, 4)}' exceeds threshold '{threshold}'.",
                            observed_value=f"annuity={annuity}, income={income}",
                        )
                    )

            delinquency = canonical_data.get("delinquency_days")
            if delinquency is not None and delinquency < 0:
                rule_violation_count += 1
                issues_to_create.append(
                    ValidationIssue(
                        id=uuid.uuid4(),
                        validation_run_id=run.id,
                        dataset_id=dataset_id,
                        source_row_number=row_num,
                        column_name=reverse_lookup.get("delinquency_days"),
                        issue_type="BUSINESS_RULE_VIOLATION",
                        severity="WARNING",
                        message=f"Delinquency days '{delinquency}' cannot be negative.",
                        observed_value=str(delinquency),
                    )
                )

            # Disbursement date checks
            disb_date_val = canonical_data.get("disbursement_date")
            if disb_date_val:
                try:
                    # Date could be a date object or a string "YYYY-MM-DD"
                    if isinstance(disb_date_val, str):
                        d_val = datetime.strptime(disb_date_val, "%Y-%m-%d").date()
                    else:
                        d_val = disb_date_val

                    if d_val > date.today():
                        rule_violation_count += 1
                        issues_to_create.append(
                            ValidationIssue(
                                id=uuid.uuid4(),
                                validation_run_id=run.id,
                                dataset_id=dataset_id,
                                source_row_number=row_num,
                                column_name=reverse_lookup.get("disbursement_date"),
                                issue_type="BUSINESS_RULE_VIOLATION",
                                severity="WARNING",
                                message=f"Disbursement date '{d_val}' is in the future.",
                                observed_value=str(disb_date_val),
                            )
                        )
                except Exception:
                    pass

            if record_has_error:
                invalid_records += 1
            else:
                valid_records += 1

        # 5. Calculate validation score (Errors heavily reduce, warnings slightly reduce)
        total_errors = sum(1 for issue in issues_to_create if issue.severity == "ERROR")
        total_warnings = sum(1 for issue in issues_to_create if issue.severity == "WARNING")
        
        error_penalty = (total_errors * 50.0) / total_records if total_records > 0 else 0.0
        warning_penalty = (total_warnings * 5.0) / total_records if total_records > 0 else 0.0
        validation_score = 100.0 - (error_penalty + warning_penalty)
        validation_score = max(0.0, min(100.0, validation_score))

        # Determine run status
        # If there are any ERROR-level issues, status is FAILED. If only WARNINGS, it's WARNING. Otherwise PASSED.
        has_errors = any(issue.severity == "ERROR" for issue in issues_to_create)
        has_warnings = any(issue.severity == "WARNING" for issue in issues_to_create)

        final_status = ValidationStatusEnum.PASSED
        if has_errors:
            final_status = ValidationStatusEnum.FAILED
        elif has_warnings:
            final_status = ValidationStatusEnum.WARNING

        # 6. Save issues in batches
        for i in range(0, len(issues_to_create), 500):
            batch = issues_to_create[i : i + 500]
            self.db.add_all(batch)
            await self.db.flush()

        # Update run stats
        run.total_records = total_records
        run.valid_records = valid_records
        run.invalid_records = invalid_records
        run.missing_value_count = missing_count
        run.duplicate_count = duplicate_count
        run.invalid_type_count = type_error_count
        run.outlier_count = outlier_count
        run.business_rule_violation_count = rule_violation_count
        run.validation_score = round(validation_score, 2)
        run.status = final_status
        run.completed_at = datetime.now(timezone.utc)
        self.db.add(run)

        # Update dataset validation status
        if dataset:
            dataset.validation_status = final_status
            self.db.add(dataset)

        await self.db.flush()
        logger.info(
            "Validation run completed for dataset_id=%s. Score: %s, Status: %s. Issues logged: %d",
            dataset_id,
            run.validation_score,
            final_status,
            len(issues_to_create),
        )
        return run

    async def get_metrics(self, dataset_id: uuid.UUID, version_id: uuid.UUID) -> Dict[str, Any]:
        """
        Retrieves complete computed metrics and visualizations structure for
        Data Quality Analytics.
        """
        logger.info("Computing Data Quality metrics for dataset_id=%s, version_id=%s", dataset_id, version_id)

        # 1. Fetch RawRecords
        records_stmt = (
            select(RawRecord)
            .where(RawRecord.dataset_id == dataset_id, RawRecord.version_id == version_id)
            .order_by(RawRecord.source_row_number.asc())
        )
        records_res = await self.db.execute(records_stmt)
        raw_records = records_res.scalars().all()
        total_records = len(raw_records)

        if total_records == 0:
            return {
                "total_records": 0,
                "valid_records": 0,
                "invalid_records": 0,
                "missing_value_count": 0,
                "missing_value_percentage": 0.0,
                "duplicate_count": 0,
                "duplicate_percentage": 0.0,
                "invalid_datatype_count": 0,
                "invalid_business_rule_count": 0,
                "outlier_count": 0,
                "completeness_score": 100.0,
                "uniqueness_score": 100.0,
                "validity_score": 100.0,
                "consistency_score": 100.0,
                "dataset_health_score": 100.0,
                "schema_drift_indicator": "unavailable: no records in version",
                "validation_trend_by_dataset_version": [],
                "visualizations": {
                    "data_quality_scorecard": {},
                    "validation_issue_table": [],
                    "missing_values_heatmap": {},
                    "invalid_records_table": [],
                    "outlier_boxplots": [],
                    "dataset_health_timeline": [],
                    "schema_mapping_status_chart": {},
                },
            }

        # 2. Get or run validation
        run_stmt = (
            select(ValidationRun)
            .where(ValidationRun.dataset_id == dataset_id, ValidationRun.version_id == version_id)
            .order_by(ValidationRun.started_at.desc())
            .limit(1)
        )
        run_res = await self.db.execute(run_stmt)
        run = run_res.scalars().first()

        if not run or run.status in (ValidationStatusEnum.PENDING, ValidationStatusEnum.VALIDATING):
            run = await self.run_validation(dataset_id, version_id)

        # Fetch validation issues
        issues_stmt = select(ValidationIssue).where(ValidationIssue.validation_run_id == run.id)
        issues_res = await self.db.execute(issues_stmt)
        issues = list(issues_res.scalars().all())

        # 3. Compute stats
        valid_records = run.valid_records
        invalid_records = run.invalid_records
        missing_value_count = run.missing_value_count
        duplicate_count = run.duplicate_count
        invalid_datatype_count = run.invalid_type_count
        invalid_business_rule_count = run.business_rule_violation_count
        outlier_count = run.outlier_count

        missing_value_percentage = (
            round((missing_value_count / (total_records * len(REQUIRED_CANONICAL_FIELDS))) * 100.0, 2)
            if REQUIRED_CANONICAL_FIELDS
            else 0.0
        )
        duplicate_percentage = round((duplicate_count / total_records) * 100.0, 2)

        completeness_score = round(max(0.0, 100.0 - missing_value_percentage), 2)
        uniqueness_score = round(max(0.0, 100.0 - duplicate_percentage), 2)
        validity_score = (
            round(max(0.0, 100.0 - (invalid_datatype_count / total_records) * 100.0), 2) if total_records > 0 else 100.0
        )
        consistency_score = (
            round(max(0.0, 100.0 - (invalid_business_rule_count / total_records) * 100.0), 2)
            if total_records > 0
            else 100.0
        )
        dataset_health_score = round(
            (completeness_score + uniqueness_score + validity_score + consistency_score) / 4.0, 2
        )

        # 4. Schema drift
        versions_stmt = (
            select(DatasetVersion)
            .where(DatasetVersion.dataset_id == dataset_id)
            .order_by(DatasetVersion.version_number.asc())
        )
        versions_res = await self.db.execute(versions_stmt)
        versions = list(versions_res.scalars().all())

        v1 = next((v for v in versions if v.version_number == 1), None)
        drift_detected = False
        added_fields = []
        removed_fields = []
        if v1 and v1.id != version_id:
            v1_mappings_stmt = select(SchemaMapping).where(
                SchemaMapping.dataset_id == dataset_id, SchemaMapping.version_id == v1.id
            )
            v1_mappings_res = await self.db.execute(v1_mappings_stmt)
            v1_mappings = v1_mappings_res.scalars().all()

            curr_mappings_stmt = select(SchemaMapping).where(
                SchemaMapping.dataset_id == dataset_id, SchemaMapping.version_id == version_id
            )
            curr_mappings_res = await self.db.execute(curr_mappings_stmt)
            curr_mappings = curr_mappings_res.scalars().all()

            v1_fields = {m.canonical_field for m in v1_mappings}
            curr_fields = {m.canonical_field for m in curr_mappings}

            added_fields = list(curr_fields - v1_fields)
            removed_fields = list(v1_fields - curr_fields)
            drift_detected = len(added_fields) > 0 or len(removed_fields) > 0

        schema_drift_indicator = {
            "drift_detected": drift_detected,
            "baseline_version_number": 1 if v1 else None,
            "added_fields": added_fields,
            "removed_fields": removed_fields,
        }

        # 5. Validation trend
        validation_trend_by_dataset_version = []
        for v in sorted(versions, key=lambda x: x.version_number):
            v_run_stmt = (
                select(ValidationRun)
                .where(ValidationRun.dataset_id == dataset_id, ValidationRun.version_id == v.id)
                .order_by(ValidationRun.started_at.desc())
                .limit(1)
            )
            v_run_res = await self.db.execute(v_run_stmt)
            v_run = v_run_res.scalars().first()

            if v_run:
                # Recalculate health score for past versions
                v_missing_pct = (
                    (v_run.missing_value_count / (v_run.total_records * len(REQUIRED_CANONICAL_FIELDS))) * 100.0
                    if v_run.total_records > 0 and REQUIRED_CANONICAL_FIELDS
                    else 0.0
                )
                v_dup_pct = (v_run.duplicate_count / v_run.total_records) * 100.0 if v_run.total_records > 0 else 0.0
                v_comp = max(0.0, 100.0 - v_missing_pct)
                v_uniq = max(0.0, 100.0 - v_dup_pct)
                v_val = (
                    max(0.0, 100.0 - (v_run.invalid_type_count / v_run.total_records) * 100.0)
                    if v_run.total_records > 0
                    else 100.0
                )
                v_cons = (
                    max(0.0, 100.0 - (v_run.business_rule_violation_count / v_run.total_records) * 100.0)
                    if v_run.total_records > 0
                    else 100.0
                )
                v_health = (v_comp + v_uniq + v_val + v_cons) / 4.0

                validation_trend_by_dataset_version.append(
                    {
                        "version_number": v.version_number,
                        "version_id": str(v.id),
                        "validation_score": v_run.validation_score,
                        "health_score": round(v_health, 2),
                        "status": v_run.status,
                        "completed_at": v_run.completed_at.isoformat() if v_run.completed_at else None,
                    }
                )

        # 6. Scorecard
        def get_rating(score: float) -> str:
            if score >= 95.0:
                return "EXCELLENT"
            if score >= 85.0:
                return "GOOD"
            if score >= 70.0:
                return "FAIR"
            return "POOR"

        data_quality_scorecard = {
            "completeness": {"score": completeness_score, "rating": get_rating(completeness_score)},
            "uniqueness": {"score": uniqueness_score, "rating": get_rating(uniqueness_score)},
            "validity": {"score": validity_score, "rating": get_rating(validity_score)},
            "consistency": {"score": consistency_score, "rating": get_rating(consistency_score)},
            "overall_health": {"score": dataset_health_score, "rating": get_rating(dataset_health_score)},
        }

        # 7. Issue table
        validation_issue_table = [
            {
                "row_number": issue.source_row_number,
                "column_name": issue.column_name,
                "issue_type": issue.issue_type,
                "severity": issue.severity,
                "message": issue.message,
                "observed_value": issue.observed_value,
            }
            for issue in issues[:100]
        ]

        # 8. Heatmap
        mappings_stmt = select(SchemaMapping).where(
            SchemaMapping.dataset_id == dataset_id, SchemaMapping.version_id == version_id
        )
        mappings_res = await self.db.execute(mappings_stmt)
        mappings = list(mappings_res.scalars().all())

        column_missing_counts = {}
        for m in mappings:
            column_missing_counts[m.original_column_name] = 0

        for rr in raw_records:
            raw_data = rr.raw_data_json or {}
            for m in mappings:
                val = raw_data.get(m.original_column_name)
                if val is None or str(val).strip() == "" or str(val).lower() in ("nan", "none", "null"):
                    column_missing_counts[m.original_column_name] += 1

        missing_values_heatmap = {
            "columns": list(column_missing_counts.keys()),
            "missing_counts": list(column_missing_counts.values()),
            "missing_percentages": [
                round((count / total_records) * 100.0, 2) for count in column_missing_counts.values()
            ],
        }

        # 9. Invalid records
        invalid_records_table = []
        issues_by_row = {}
        for issue in issues:
            if issue.source_row_number not in issues_by_row:
                issues_by_row[issue.source_row_number] = []
            issues_by_row[issue.source_row_number].append(issue)

        for rr in raw_records:
            row_num = rr.source_row_number
            if row_num in issues_by_row:
                row_issues = issues_by_row[row_num]
                if any(i.severity in ("ERROR", "WARNING") for i in row_issues):
                    invalid_records_table.append(
                        {
                            "row_number": row_num,
                            "raw_data": rr.raw_data_json,
                            "issues": [
                                {
                                    "column_name": i.column_name,
                                    "issue_type": i.issue_type,
                                    "severity": i.severity,
                                    "message": i.message,
                                    "observed_value": i.observed_value,
                                }
                                for i in row_issues
                            ],
                        }
                    )
                    if len(invalid_records_table) >= 50:
                        break

        # 10. Outliers boxplot
        outlier_boxplots = []
        numeric_fields = [
            "age",
            "income",
            "loan_amount",
            "interest_rate",
            "loan_term",
            "outstanding_amount",
            "annuity_amount",
            "asset_value",
            "delinquency_days",
            "family_size",
            "repayment_burden_ratio",
        ]
        mapped_numeric_fields = [m.canonical_field for m in mappings if m.canonical_field in numeric_fields]

        for field in mapped_numeric_fields:
            vals = []
            for rr in raw_records:
                canon_data = rr.canonical_data_json or {}
                v = canon_data.get(field)
                if v is not None:
                    try:
                        vals.append(float(v))
                    except (ValueError, TypeError):
                        pass

            if vals:
                median_val = calculate_median(vals)
                q1, q3, lower, upper = calculate_iqr_bounds(vals)
                outliers = [x for x in vals if x < lower or x > upper]
                normal_vals = [x for x in vals if lower <= x <= upper]
                min_val = min(normal_vals) if normal_vals else min(vals)
                max_val = max(normal_vals) if normal_vals else max(vals)

                outlier_boxplots.append(
                    {
                        "canonical_field": field,
                        "min": min_val,
                        "q1": q1,
                        "median": median_val,
                        "q3": q3,
                        "max": max_val,
                        "lower_bound": lower,
                        "upper_bound": upper,
                        "outlier_count": len(outliers),
                        "outliers": outliers[:50],
                    }
                )

        # 11. Timeline
        dataset_health_timeline = [
            {
                "version_number": t["version_number"],
                "health_score": t["health_score"],
                "status": t["status"],
                "completed_at": t["completed_at"],
            }
            for t in validation_trend_by_dataset_version
        ]

        # 12. Schema status chart
        first_record_cols = list(raw_records[0].raw_data_json.keys()) if raw_records else []
        total_columns = len(first_record_cols)
        schema_mapping_status_chart = {
            "total_columns": total_columns,
            "mapped_count": len(mappings),
            "unmapped_count": max(0, total_columns - len(mappings)),
            "mappings": [
                {
                    "original_column": m.original_column_name,
                    "canonical_field": m.canonical_field,
                    "confidence_score": m.confidence_score,
                    "source": m.mapping_source,
                }
                for m in mappings
            ],
        }

        return {
            "total_records": total_records,
            "valid_records": valid_records,
            "invalid_records": invalid_records,
            "missing_value_count": missing_value_count,
            "missing_value_percentage": missing_value_percentage,
            "duplicate_count": duplicate_count,
            "duplicate_percentage": duplicate_percentage,
            "invalid_datatype_count": invalid_datatype_count,
            "invalid_business_rule_count": invalid_business_rule_count,
            "outlier_count": outlier_count,
            "completeness_score": completeness_score,
            "uniqueness_score": uniqueness_score,
            "validity_score": validity_score,
            "consistency_score": consistency_score,
            "dataset_health_score": dataset_health_score,
            "schema_drift_indicator": schema_drift_indicator,
            "validation_trend_by_dataset_version": validation_trend_by_dataset_version,
            "visualizations": {
                "data_quality_scorecard": data_quality_scorecard,
                "validation_issue_table": validation_issue_table,
                "missing_values_heatmap": missing_values_heatmap,
                "invalid_records_table": invalid_records_table,
                "outlier_boxplots": outlier_boxplots,
                "dataset_health_timeline": dataset_health_timeline,
                "schema_mapping_status_chart": schema_mapping_status_chart,
            },
        }
