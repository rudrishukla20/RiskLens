import os
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import log_audit_action
from app.enums.audit_action import AuditActionEnum
from app.enums.dataset_status import DatasetStatusEnum
from app.enums.validation_status import ValidationStatusEnum
from app.exceptions.base import NotFoundException
from app.models.dataset import Dataset
from app.models.dataset_column import DatasetColumn
from app.models.dataset_file import DatasetFile
from app.models.dataset_version import DatasetVersion
from app.models.user import User
from app.repositories.dataset_repository import DatasetRepository
from app.utils.file import generate_safe_filename, sanitize_and_check_path, validate_file_size
from app.utils.validators import validate_structured_file


class DatasetService:
    """Service managing structured dataset upload lifecycles and metadata catalog queries."""

    def __init__(self, db: AsyncSession, user: User) -> None:
        self.db = db
        self.user = user
        self.dataset_repo = DatasetRepository(db)

    async def upload_dataset(
        self,
        name: str,
        original_filename: str,
        file_size_bytes: int,
        temp_file_path: str,
        description: Optional[str] = None,
    ) -> Dataset:
        """
        Orchestrates dataset upload validation.
        Moves files to safe storage, populates catalog records (v1), and returns metadata.
        """
        # 1. Size Validation
        validate_file_size(file_size_bytes)

        # 2. File Extension and Type Validation
        file_type = validate_structured_file(original_filename)

        # 3. Secure Target Path Calculation
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        stored_file_name = generate_safe_filename(original_filename)
        storage_path = sanitize_and_check_path(settings.UPLOAD_DIR, stored_file_name)

        # Copy the uploaded file to target storage_path
        import shutil
        shutil.copy(temp_file_path, storage_path)

        # Read dataset file and parse schema
        ext = os.path.splitext(original_filename.lower())[1]
        try:
            from app.ingestion.csv_reader import read_csv
            from app.ingestion.excel_reader import read_excel
            from app.ingestion.json_reader import read_json
            from app.ingestion.schema_inferer import infer_schema
            from app.ingestion.schema_mapper import persist_inferred_columns

            if ext == ".csv":
                df, _ = read_csv(storage_path)
            elif ext in (".xlsx", ".xls"):
                df, _ = read_excel(storage_path)
            elif ext == ".json":
                df, _ = read_json(storage_path)
            else:
                raise ValueError(f"Unsupported file type: {ext}")
            
            record_count = len(df)
            column_count = len(df.columns)
            inferred = infer_schema(df)
        except Exception as e:
            # Cleanup storage path if parsing fails
            if os.path.exists(storage_path):
                os.remove(storage_path)
            raise ValueError(f"Failed to parse dataset file: {e}")

        # 4. Create Core Dataset Record
        dataset = await self.dataset_repo.create(
            {
                "name": name,
                "description": description,
                "original_file_name": original_filename,
                "file_type": file_type,
                "uploaded_by": self.user.id,
                "upload_status": DatasetStatusEnum.UPLOADED,
                "validation_status": ValidationStatusEnum.PENDING,
                "profiling_status": DatasetStatusEnum.UPLOADED,
                "analysis_status": DatasetStatusEnum.UPLOADED,
                "storage_path": storage_path,
                "record_count": record_count,
                "column_count": column_count,
            }
        )

        # 5. Create Initial Version (v1)
        version = DatasetVersion(
            id=uuid.uuid4(),
            dataset_id=dataset.id,
            version_number=1,
            row_count=record_count,
            column_count=column_count,
            storage_path=storage_path,
            created_by=self.user.id,
        )
        await self.dataset_repo.create_version(version)

        # Link Dataset Active Version
        dataset.active_version_id = version.id
        self.db.add(dataset)

        # Persist inferred columns to database
        await persist_inferred_columns(self.db, dataset.id, version.id, inferred)

        # 6. Create Initial File Row
        file_record = DatasetFile(
            id=uuid.uuid4(),
            dataset_id=dataset.id,
            version_id=version.id,
            original_file_name=original_filename,
            stored_file_name=stored_file_name,
            file_extension=os.path.splitext(original_filename.lower())[1],
            mime_type=None,
            file_size_bytes=file_size_bytes,
            storage_path=storage_path,
        )
        await self.dataset_repo.create_file(file_record)

        await log_audit_action(
            self.db,
            user_id=self.user.id,
            action=AuditActionEnum.DATASET_UPLOADED,
            module_name="dataset",
            resource_type="Dataset",
            resource_id=str(dataset.id),
            details={"filename": original_filename, "version": 1},
        )

        return dataset

    async def list_datasets(self, *, skip: int = 0, limit: int = 100) -> List[Dataset]:
        """Lists active datasets."""
        from sqlalchemy import select
        stmt = (
            select(Dataset)
            .where(Dataset.archived_at.is_(None))
            .offset(skip)
            .limit(limit)
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def get_dataset(self, dataset_id: uuid.UUID) -> Dataset:
        """Fetches details of a specific dataset."""
        dataset = await self.dataset_repo.get(dataset_id)
        if not dataset:
            raise NotFoundException(message="Dataset not found.")
        return dataset

    async def archive_dataset(self, dataset_id: uuid.UUID) -> Dataset:
        """Archives a dataset by marking its archived_at timestamp."""
        dataset = await self.get_dataset(dataset_id)
        dataset.archived_at = datetime.now(timezone.utc)
        self.db.add(dataset)

        await log_audit_action(
            self.db,
            user_id=self.user.id,
            action=AuditActionEnum.DATASET_ARCHIVED,
            module_name="dataset",
            resource_type="Dataset",
            resource_id=str(dataset_id),
        )
        await self.db.flush()
        return dataset

    async def get_columns(self, dataset_id: uuid.UUID) -> List[DatasetColumn]:
        """Fetches mapping columns configured for a dataset."""
        dataset = await self.get_dataset(dataset_id)
        return await self.dataset_repo.get_columns(dataset_id, dataset.active_version_id)

    async def upload_dataset_version(
        self,
        dataset_id: uuid.UUID,
        original_filename: str,
        file_size_bytes: int,
        temp_file_path: str,
    ) -> DatasetVersion:
        """
        Orchestrates dataset version upload validation, saves DatasetVersion,
        copies confirmed schema mapping rules from the previous version,
        and triggers the canonical transformation, risk assessments, and portfolio analytics.
        """
        # 1. Size Validation
        validate_file_size(file_size_bytes)

        # 2. File Extension and Type Validation
        file_type = validate_structured_file(original_filename)

        # Get target dataset
        dataset = await self.get_dataset(dataset_id)

        # 3. Secure Target Path Calculation
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        stored_file_name = generate_safe_filename(original_filename)
        storage_path = sanitize_and_check_path(settings.UPLOAD_DIR, stored_file_name)

        # Copy the uploaded file to target storage_path
        import shutil
        shutil.copy(temp_file_path, storage_path)

        # Read dataset file and parse schema
        ext = os.path.splitext(original_filename.lower())[1]
        try:
            from app.ingestion.csv_reader import read_csv
            from app.ingestion.excel_reader import read_excel
            from app.ingestion.json_reader import read_json
            from app.ingestion.schema_inferer import infer_schema
            from app.ingestion.schema_mapper import persist_inferred_columns

            if ext == ".csv":
                df, _ = read_csv(storage_path)
            elif ext in (".xlsx", ".xls"):
                df, _ = read_excel(storage_path)
            elif ext == ".json":
                df, _ = read_json(storage_path)
            else:
                raise ValueError(f"Unsupported file type: {ext}")
            
            record_count = len(df)
            column_count = len(df.columns)
            inferred = infer_schema(df)
        except Exception as e:
            if os.path.exists(storage_path):
                os.remove(storage_path)
            raise ValueError(f"Failed to parse dataset version file: {e}")

        # Determine next version_number
        from sqlalchemy import select, func
        stmt = select(func.max(DatasetVersion.version_number)).where(DatasetVersion.dataset_id == dataset_id)
        max_res = await self.db.execute(stmt)
        max_ver = max_res.scalar() or 0
        next_ver_number = max_ver + 1

        # Create Version record
        version = DatasetVersion(
            id=uuid.uuid4(),
            dataset_id=dataset.id,
            version_number=next_ver_number,
            row_count=record_count,
            column_count=column_count,
            storage_path=storage_path,
            created_by=self.user.id,
        )
        await self.dataset_repo.create_version(version)

        # Update core dataset properties
        dataset.active_version_id = version.id
        dataset.storage_path = storage_path
        dataset.record_count = record_count
        dataset.column_count = column_count
        dataset.upload_status = DatasetStatusEnum.UPLOADED
        dataset.validation_status = ValidationStatusEnum.PENDING
        dataset.profiling_status = DatasetStatusEnum.UPLOADED
        dataset.analysis_status = DatasetStatusEnum.UPLOADED
        self.db.add(dataset)

        # Persist inferred columns to database for the new version
        await persist_inferred_columns(self.db, dataset.id, version.id, inferred)

        # Create DatasetFile record
        file_record = DatasetFile(
            id=uuid.uuid4(),
            dataset_id=dataset.id,
            version_id=version.id,
            original_file_name=original_filename,
            stored_file_name=stored_file_name,
            file_extension=ext,
            mime_type=None,
            file_size_bytes=file_size_bytes,
            storage_path=storage_path,
        )
        await self.dataset_repo.create_file(file_record)

        # Copy mappings from previous version
        if max_ver > 0:
            prev_ver_stmt = select(DatasetVersion).where(
                DatasetVersion.dataset_id == dataset_id,
                DatasetVersion.version_number == max_ver
            )
            prev_ver_res = await self.db.execute(prev_ver_stmt)
            prev_ver = prev_ver_res.scalar_one_or_none()
            if prev_ver:
                from app.models.schema_mapping import SchemaMapping
                mapping_stmt = select(SchemaMapping).where(
                    SchemaMapping.dataset_id == dataset_id,
                    SchemaMapping.version_id == prev_ver.id
                )
                mapping_res = await self.db.execute(mapping_stmt)
                prev_mappings = mapping_res.scalars().all()
                for m in prev_mappings:
                    new_mapping = SchemaMapping(
                        id=uuid.uuid4(),
                        dataset_id=dataset_id,
                        version_id=version.id,
                        original_column_name=m.original_column_name,
                        canonical_field=m.canonical_field,
                        confidence_score=m.confidence_score,
                        mapping_source=m.mapping_source,
                        confirmed_by=self.user.id,
                        confirmed_at=datetime.now(timezone.utc),
                    )
                    self.db.add(new_mapping)
                await self.db.flush()

        # Phase 2: Downstream triggers (Canonical transformation, risk assessments, and portfolio analytics)
        # 1. Transform raw records, group borrowers, extract loans
        from app.ingestion.canonical_transformer import transform_and_populate
        await transform_and_populate(self.db, dataset.id, version.id, df)

        # 2. Trigger Risk scoring engine assessments
        from app.services.risk_rule_service import RiskRuleService
        risk_service = RiskRuleService(self.db, self.user)
        await risk_service.run_risk_assessment(dataset.id, version.id)

        # 3. Trigger Portfolio aggregates computations suite
        from app.services.portfolio_service import PortfolioService
        portfolio_service = PortfolioService(self.db, self.user)
        await portfolio_service.run_portfolio_analysis(dataset.id, version.id)

        # 4. Trigger Data Quality Validation run automatically
        from app.analytics.data_quality_engine import DataQualityEngine
        dq_engine = DataQualityEngine(self.db)
        await dq_engine.run_validation(dataset.id, version.id, self.user.id)

        # Log audit action
        await log_audit_action(
            self.db,
            user_id=self.user.id,
            action=AuditActionEnum.DATASET_UPLOADED,
            module_name="dataset",
            resource_type="Dataset",
            resource_id=str(dataset.id),
            details={"filename": original_filename, "version": next_ver_number},
        )

        await self.db.flush()
        return version
