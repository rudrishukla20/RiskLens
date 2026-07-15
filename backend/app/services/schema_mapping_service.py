import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import log_audit_action
from app.enums.audit_action import AuditActionEnum
from app.models.schema_mapping import SchemaMapping
from app.models.user import User
from app.repositories.dataset_repository import DatasetRepository
from app.repositories.schema_mapping_repository import SchemaMappingRepository
from app.utils.strings import normalize_column_name


class SchemaMappingService:
    """Service to predict and store column header canonical mappings rules."""

    def __init__(self, db: AsyncSession, user: User) -> None:
        self.db = db
        self.user = user
        self.dataset_repo = DatasetRepository(db)
        self.mapping_repo = SchemaMappingRepository(db)

    async def get_mapping_suggestions(self, dataset_id: uuid.UUID) -> List[Dict[str, Any]]:
        """
        Calculates suggested mapping alignments based on header strings similarity checks.
        No ML/DL model is executed by design.
        """
        # Fetch active version id
        datasetstmt = await self.dataset_repo.get(dataset_id)
        if not datasetstmt:
            return []

        columns = await self.dataset_repo.get_columns(dataset_id, datasetstmt.active_version_id)
        suggestions = []

        # Simple rule-based similarity mapping
        # Maps common headers to their canonical identifiers
        canonical_map = {
            "age": "age",
            "gender": "gender",
            "sex": "gender",
            "income": "income",
            "annual_income": "income",
            "salary": "income",
            "employment": "employment_type",
            "job": "occupation",
            "loan_amount": "loan_amount",
            "amount": "loan_amount",
            "interest_rate": "interest_rate",
            "rate": "interest_rate",
            "loan_term": "loan_term",
            "term": "loan_term",
        }

        for col in columns:
            normalized = normalize_column_name(col.original_column_name)
            suggested = None
            confidence = 0.0

            # Check direct exact or sub-string matches
            for key, canonical in canonical_map.items():
                if key in normalized or normalized in key:
                    suggested = canonical
                    confidence = 0.85
                    break

            suggestions.append(
                {
                    "original_column_name": col.original_column_name,
                    "suggested_canonical_field": suggested,
                    "confidence_score": confidence,
                }
            )

        return suggestions

    async def confirm_mappings(
        self, dataset_id: uuid.UUID, confirmed_mappings: List[Dict[str, str]]
    ) -> List[SchemaMapping]:
        """Saves confirmed headers mappings rules to the database."""
        dataset = await self.dataset_repo.get(dataset_id)
        if not dataset:
            raise ValueError("Dataset not found.")

        active_version_id = dataset.active_version_id

        # 1. Clear old mappings to prevent overlaps
        await self.mapping_repo.delete_by_dataset(dataset_id, active_version_id)

        # 2. Insert mappings
        saved_mappings = []
        for rule in confirmed_mappings:
            mapping = SchemaMapping(
                id=uuid.uuid4(),
                dataset_id=dataset_id,
                version_id=active_version_id,
                original_column_name=rule["original_column_name"],
                canonical_field=rule["canonical_field"],
                confidence_score=1.0,
                mapping_source="MANUAL",
                confirmed_by=self.user.id,
                confirmed_at=datetime.now(timezone.utc),
            )
            self.db.add(mapping)
            saved_mappings.append(mapping)

        await log_audit_action(
            self.db,
            user_id=self.user.id,
            action=AuditActionEnum.SCHEMA_MAPPING_CONFIRMED,
            module_name="dataset",
            resource_type="Dataset",
            resource_id=str(dataset_id),
            details={"mappings_count": len(confirmed_mappings)},
        )

        # Trigger downstream extraction and analytics generation pipelines
        import os
        from app.ingestion.csv_reader import read_csv
        from app.ingestion.excel_reader import read_excel
        from app.ingestion.json_reader import read_json
        from app.ingestion.canonical_transformer import transform_and_populate
        from app.services.risk_rule_service import RiskRuleService
        from app.services.portfolio_service import PortfolioService
        from sqlalchemy import delete
        from app.models.raw_record import RawRecord
        from app.models.borrower import Borrower
        from app.models.loan import Loan
        from app.models.risk_assessment import RiskAssessment

        # 1. Clear previous run domain models and outputs
        await self.db.execute(
            delete(RiskAssessment).where(
                RiskAssessment.dataset_id == dataset_id, RiskAssessment.version_id == active_version_id
            )
        )
        await self.db.execute(
            delete(RawRecord).where(
                RawRecord.dataset_id == dataset_id, RawRecord.version_id == active_version_id
            )
        )
        await self.db.execute(
            delete(Loan).where(
                Loan.dataset_id == dataset_id, Loan.version_id == active_version_id
            )
        )
        await self.db.execute(
            delete(Borrower).where(
                Borrower.dataset_id == dataset_id, Borrower.version_id == active_version_id
            )
        )
        await self.db.flush()

        # 2. Read dataset file to pandas dataframe
        ext = os.path.splitext(dataset.original_file_name.lower())[1]
        if ext == ".csv":
            df, _ = read_csv(dataset.storage_path)
        elif ext in (".xlsx", ".xls"):
            df, _ = read_excel(dataset.storage_path)
        elif ext == ".json":
            df, _ = read_json(dataset.storage_path)
        else:
            raise ValueError(f"Unsupported file type: {ext}")

        # 3. Transform raw records, group borrowers, extract loans
        await transform_and_populate(self.db, dataset_id, active_version_id, df)

        # 4. Trigger Risk scoring engine assessments
        risk_service = RiskRuleService(self.db, self.user)
        await risk_service.run_risk_assessment(dataset_id, active_version_id)

        # 5. Trigger Portfolio aggregates computations suite
        portfolio_service = PortfolioService(self.db, self.user)
        await portfolio_service.run_portfolio_analysis(dataset_id, active_version_id)

        # 6. Trigger Data Quality Validation run automatically
        from app.analytics.data_quality_engine import DataQualityEngine
        dq_engine = DataQualityEngine(self.db)
        await dq_engine.run_validation(dataset_id, active_version_id, self.user.id)

        await self.db.flush()
        return saved_mappings
