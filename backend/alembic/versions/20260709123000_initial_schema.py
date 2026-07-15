"""Initial schema migration with 30 tables.

Revision ID: 20260709123000
Revises: None
Create Date: 2026-07-09 12:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260709123000"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. roles
    op.create_table(
        "roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_roles_code"), "roles", ["code"], unique=True)

    # 2. users
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("deactivated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_role_id"), "users", ["role_id"], unique=False)

    # 3. refresh_tokens
    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_ip", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_refresh_tokens_token_hash"), "refresh_tokens", ["token_hash"], unique=True)
    op.create_index(op.f("ix_refresh_tokens_user_id"), "refresh_tokens", ["user_id"], unique=False)

    # 4. public_dataset_sources
    op.create_table(
        "public_dataset_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("provider", sa.String(length=255), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("dataset_category", sa.String(length=100), nullable=True),
        sa.Column("access_type", sa.String(length=50), nullable=True),
        sa.Column("recommended_use", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    # 5. audit_logs
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("action", sa.String(length=60), nullable=False),
        sa.Column("module_name", sa.String(length=100), nullable=True),
        sa.Column("resource_type", sa.String(length=100), nullable=True),
        sa.Column("resource_id", sa.String(length=64), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("details_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_logs_action"), "audit_logs", ["action"], unique=False)
    op.create_index(op.f("ix_audit_logs_created_at"), "audit_logs", ["created_at"], unique=False)
    op.create_index(op.f("ix_audit_logs_request_id"), "audit_logs", ["request_id"], unique=False)
    op.create_index(op.f("ix_audit_logs_user_id"), "audit_logs", ["user_id"], unique=False)

    # 6. datasets
    op.create_table(
        "datasets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source_type", sa.String(length=100), nullable=True),
        sa.Column("original_file_name", sa.String(length=512), nullable=False),
        sa.Column("file_type", sa.String(length=10), nullable=False),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("upload_status", sa.String(length=50), nullable=False),
        sa.Column("validation_status", sa.String(length=50), nullable=False),
        sa.Column("profiling_status", sa.String(length=50), nullable=False),
        sa.Column("analysis_status", sa.String(length=50), nullable=False),
        sa.Column("record_count", sa.BigInteger(), nullable=True),
        sa.Column("column_count", sa.Integer(), nullable=True),
        sa.Column("active_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("storage_path", sa.String(length=1024), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_datasets_name"), "datasets", ["name"], unique=False)
    op.create_index(op.f("ix_datasets_uploaded_by"), "datasets", ["uploaded_by"], unique=False)

    # 7. dataset_versions
    op.create_table(
        "dataset_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("file_hash", sa.String(length=64), nullable=True),
        sa.Column("schema_hash", sa.String(length=64), nullable=True),
        sa.Column("row_count", sa.BigInteger(), nullable=True),
        sa.Column("column_count", sa.Integer(), nullable=True),
        sa.Column("storage_path", sa.String(length=1024), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_dataset_versions_dataset_id"), "dataset_versions", ["dataset_id"], unique=False)

    # Add active_version_id FK constraint to datasets now that dataset_versions exists
    op.create_foreign_key(
        "fk_datasets_active_version_id",
        "datasets",
        "dataset_versions",
        ["active_version_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # 8. dataset_files
    op.create_table(
        "dataset_files",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("original_file_name", sa.String(length=512), nullable=False),
        sa.Column("stored_file_name", sa.String(length=512), nullable=False),
        sa.Column("file_extension", sa.String(length=20), nullable=False),
        sa.Column("mime_type", sa.String(length=127), nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("storage_path", sa.String(length=1024), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["version_id"], ["dataset_versions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_dataset_files_checksum_sha256"), "dataset_files", ["checksum_sha256"], unique=False)
    op.create_index(op.f("ix_dataset_files_dataset_id"), "dataset_files", ["dataset_id"], unique=False)
    op.create_index(op.f("ix_dataset_files_version_id"), "dataset_files", ["version_id"], unique=False)

    # 9. dataset_columns
    op.create_table(
        "dataset_columns",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("original_column_name", sa.String(length=255), nullable=False),
        sa.Column("canonical_column_name", sa.String(length=255), nullable=True),
        sa.Column("inferred_data_type", sa.String(length=50), nullable=True),
        sa.Column("mapped_data_type", sa.String(length=50), nullable=True),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_mapped", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("sample_values_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["version_id"], ["dataset_versions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_dataset_columns_dataset_id"), "dataset_columns", ["dataset_id"], unique=False)
    op.create_index(op.f("ix_dataset_columns_version_id"), "dataset_columns", ["version_id"], unique=False)

    # 10. schema_mappings
    op.create_table(
        "schema_mappings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("original_column_name", sa.String(length=255), nullable=False),
        sa.Column("canonical_field", sa.String(length=255), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("mapping_source", sa.String(length=50), nullable=False, server_default="AUTO"),
        sa.Column("confirmed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["confirmed_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["version_id"], ["dataset_versions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_schema_mappings_dataset_id"), "schema_mappings", ["dataset_id"], unique=False)
    op.create_index(op.f("ix_schema_mappings_version_id"), "schema_mappings", ["version_id"], unique=False)

    # 11. raw_records
    op.create_table(
        "raw_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_row_number", sa.BigInteger(), nullable=False),
        sa.Column("raw_data_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("canonical_data_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("validation_status", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["version_id"], ["dataset_versions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_raw_records_dataset_id"), "raw_records", ["dataset_id"], unique=False)
    op.create_index(op.f("ix_raw_records_version_id"), "raw_records", ["version_id"], unique=False)

    # 12. borrowers
    op.create_table(
        "borrowers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_borrower_id", sa.String(length=255), nullable=True),
        sa.Column("age", sa.Integer(), nullable=True),
        sa.Column("gender", sa.String(length=50), nullable=True),
        sa.Column("income", sa.Float(), nullable=True),
        sa.Column("employment_type", sa.String(length=100), nullable=True),
        sa.Column("education_level", sa.String(length=100), nullable=True),
        sa.Column("marital_status", sa.String(length=50), nullable=True),
        sa.Column("region", sa.String(length=100), nullable=True),
        sa.Column("occupation", sa.String(length=100), nullable=True),
        sa.Column("housing_type", sa.String(length=100), nullable=True),
        sa.Column("family_size", sa.Integer(), nullable=True),
        sa.Column("additional_attributes_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["version_id"], ["dataset_versions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_borrowers_dataset_id"), "borrowers", ["dataset_id"], unique=False)
    op.create_index(op.f("ix_borrowers_source_borrower_id"), "borrowers", ["source_borrower_id"], unique=False)
    op.create_index(op.f("ix_borrowers_version_id"), "borrowers", ["version_id"], unique=False)

    # 13. loans
    op.create_table(
        "loans",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("borrower_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_loan_id", sa.String(length=255), nullable=True),
        sa.Column("loan_amount", sa.Float(), nullable=True),
        sa.Column("loan_purpose", sa.String(length=255), nullable=True),
        sa.Column("interest_rate", sa.Float(), nullable=True),
        sa.Column("loan_term", sa.Integer(), nullable=True),
        sa.Column("loan_status", sa.String(length=100), nullable=True),
        sa.Column("disbursement_date", sa.Date(), nullable=True),
        sa.Column("outstanding_amount", sa.Float(), nullable=True),
        sa.Column("annuity_amount", sa.Float(), nullable=True),
        sa.Column("repayment_burden_ratio", sa.Float(), nullable=True),
        sa.Column("delinquency_days", sa.Integer(), nullable=True),
        sa.Column("historical_default_flag", sa.Boolean(), nullable=True),
        sa.Column("asset_value", sa.Float(), nullable=True),
        sa.Column("additional_attributes_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["borrower_id"], ["borrowers.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["version_id"], ["dataset_versions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_loans_borrower_id"), "loans", ["borrower_id"], unique=False)
    op.create_index(op.f("ix_loans_dataset_id"), "loans", ["dataset_id"], unique=False)
    op.create_index(op.f("ix_loans_source_loan_id"), "loans", ["source_loan_id"], unique=False)
    op.create_index(op.f("ix_loans_version_id"), "loans", ["version_id"], unique=False)

    # 14. validation_runs
    op.create_table(
        "validation_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("total_records", sa.BigInteger(), nullable=False),
        sa.Column("valid_records", sa.BigInteger(), nullable=False),
        sa.Column("invalid_records", sa.BigInteger(), nullable=False),
        sa.Column("missing_value_count", sa.BigInteger(), nullable=False),
        sa.Column("duplicate_count", sa.BigInteger(), nullable=False),
        sa.Column("invalid_type_count", sa.BigInteger(), nullable=False),
        sa.Column("outlier_count", sa.BigInteger(), nullable=False),
        sa.Column("business_rule_violation_count", sa.BigInteger(), nullable=False),
        sa.Column("validation_score", sa.Float(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["version_id"], ["dataset_versions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_validation_runs_dataset_id"), "validation_runs", ["dataset_id"], unique=False)
    op.create_index(op.f("ix_validation_runs_version_id"), "validation_runs", ["version_id"], unique=False)

    # 15. validation_issues
    op.create_table(
        "validation_issues",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("validation_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_row_number", sa.BigInteger(), nullable=True),
        sa.Column("column_name", sa.String(length=255), nullable=True),
        sa.Column("issue_type", sa.String(length=100), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("observed_value", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["validation_run_id"], ["validation_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_validation_issues_dataset_id"), "validation_issues", ["dataset_id"], unique=False)
    op.create_index(
        op.f("ix_validation_issues_validation_run_id"), "validation_issues", ["validation_run_id"], unique=False
    )

    # 16. profile_runs
    op.create_table(
        "profile_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("row_count", sa.BigInteger(), nullable=True),
        sa.Column("column_count", sa.Integer(), nullable=True),
        sa.Column("missing_percentage", sa.Float(), nullable=True),
        sa.Column("duplicate_percentage", sa.Float(), nullable=True),
        sa.Column("dataset_health_score", sa.Float(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["version_id"], ["dataset_versions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_profile_runs_dataset_id"), "profile_runs", ["dataset_id"], unique=False)
    op.create_index(op.f("ix_profile_runs_version_id"), "profile_runs", ["version_id"], unique=False)

    # 17. column_profiles
    op.create_table(
        "column_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("profile_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("column_name", sa.String(length=255), nullable=False),
        sa.Column("data_type", sa.String(length=50), nullable=True),
        sa.Column("missing_count", sa.BigInteger(), nullable=True),
        sa.Column("missing_percentage", sa.Float(), nullable=True),
        sa.Column("unique_count", sa.BigInteger(), nullable=True),
        sa.Column("mean_value", sa.Float(), nullable=True),
        sa.Column("median_value", sa.Float(), nullable=True),
        sa.Column("min_value", sa.Float(), nullable=True),
        sa.Column("max_value", sa.Float(), nullable=True),
        sa.Column("std_dev", sa.Float(), nullable=True),
        sa.Column("percentile_25", sa.Float(), nullable=True),
        sa.Column("percentile_75", sa.Float(), nullable=True),
        sa.Column("outlier_count", sa.BigInteger(), nullable=True),
        sa.Column("distribution_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["profile_run_id"], ["profile_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_column_profiles_dataset_id"), "column_profiles", ["dataset_id"], unique=False)
    op.create_index(op.f("ix_column_profiles_profile_run_id"), "column_profiles", ["profile_run_id"], unique=False)

    # 18. documents
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("original_file_name", sa.String(length=512), nullable=False),
        sa.Column("document_type", sa.String(length=100), nullable=True),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("upload_status", sa.String(length=50), nullable=False),
        sa.Column("analysis_status", sa.String(length=50), nullable=False),
        sa.Column("storage_path", sa.String(length=1024), nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_documents_checksum_sha256"), "documents", ["checksum_sha256"], unique=False)
    op.create_index(op.f("ix_documents_dataset_id"), "documents", ["dataset_id"], unique=False)
    op.create_index(op.f("ix_documents_uploaded_by"), "documents", ["uploaded_by"], unique=False)

    # 19. document_extractions
    op.create_table(
        "document_extractions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("extracted_tables_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("extraction_status", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_document_extractions_document_id"), "document_extractions", ["document_id"], unique=False)

    # 20. document_analysis_results
    op.create_table(
        "document_analysis_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("executive_summary", sa.Text(), nullable=True),
        sa.Column("key_findings_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("risk_notes_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("compliance_observations_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("extracted_financial_ratios_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_document_analysis_results_document_id"), "document_analysis_results", ["document_id"], unique=False
    )

    # 21. risk_assessments
    op.create_table(
        "risk_assessments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("borrower_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("loan_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("risk_score", sa.Float(), nullable=False),
        sa.Column("risk_category", sa.String(length=20), nullable=False),
        sa.Column("risk_driver_summary", sa.Text(), nullable=True),
        sa.Column("assessment_version", sa.Integer(), nullable=False),
        sa.Column("rule_set_version", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["borrower_id"], ["borrowers.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["loan_id"], ["loans.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["version_id"], ["dataset_versions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_risk_assessments_borrower_id"), "risk_assessments", ["borrower_id"], unique=False)
    op.create_index(op.f("ix_risk_assessments_dataset_id"), "risk_assessments", ["dataset_id"], unique=False)
    op.create_index(op.f("ix_risk_assessments_loan_id"), "risk_assessments", ["loan_id"], unique=False)
    op.create_index(op.f("ix_risk_assessments_version_id"), "risk_assessments", ["version_id"], unique=False)

    # 22. risk_driver_breakdowns
    op.create_table(
        "risk_driver_breakdowns",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("risk_assessment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("driver_name", sa.String(length=255), nullable=False),
        sa.Column("driver_value", sa.Text(), nullable=True),
        sa.Column("driver_weight", sa.Float(), nullable=True),
        sa.Column("contribution_score", sa.Float(), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["risk_assessment_id"], ["risk_assessments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_risk_driver_breakdowns_risk_assessment_id"),
        "risk_driver_breakdowns",
        ["risk_assessment_id"],
        unique=False,
    )

    # 23. portfolio_snapshots
    op.create_table(
        "portfolio_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("portfolio_value", sa.Float(), nullable=True),
        sa.Column("total_loans", sa.Integer(), nullable=True),
        sa.Column("total_borrowers", sa.Integer(), nullable=True),
        sa.Column("outstanding_exposure", sa.Float(), nullable=True),
        sa.Column("high_risk_exposure", sa.Float(), nullable=True),
        sa.Column("average_risk_score", sa.Float(), nullable=True),
        sa.Column("average_loan_size", sa.Float(), nullable=True),
        sa.Column("concentration_index", sa.Float(), nullable=True),
        sa.Column("diversification_index", sa.Float(), nullable=True),
        sa.Column("snapshot_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["version_id"], ["dataset_versions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_portfolio_snapshots_dataset_id"), "portfolio_snapshots", ["dataset_id"], unique=False)
    op.create_index(
        op.f("ix_portfolio_snapshots_snapshot_date"), "portfolio_snapshots", ["snapshot_date"], unique=False
    )
    op.create_index(op.f("ix_portfolio_snapshots_version_id"), "portfolio_snapshots", ["version_id"], unique=False)

    # 24. portfolio_segment_metrics
    op.create_table(
        "portfolio_segment_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("segment_type", sa.String(length=100), nullable=False),
        sa.Column("segment_value", sa.String(length=255), nullable=False),
        sa.Column("borrower_count", sa.Integer(), nullable=True),
        sa.Column("loan_count", sa.Integer(), nullable=True),
        sa.Column("portfolio_value", sa.Float(), nullable=True),
        sa.Column("outstanding_exposure", sa.Float(), nullable=True),
        sa.Column("average_risk_score", sa.Float(), nullable=True),
        sa.Column("high_risk_count", sa.Integer(), nullable=True),
        sa.Column("high_risk_exposure", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["version_id"], ["dataset_versions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_portfolio_segment_metrics_dataset_id"), "portfolio_segment_metrics", ["dataset_id"], unique=False
    )
    op.create_index(
        op.f("ix_portfolio_segment_metrics_version_id"), "portfolio_segment_metrics", ["version_id"], unique=False
    )

    # 25. concentration_metrics
    op.create_table(
        "concentration_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("concentration_type", sa.String(length=100), nullable=False),
        sa.Column("concentration_key", sa.String(length=255), nullable=False),
        sa.Column("exposure_amount", sa.Float(), nullable=True),
        sa.Column("exposure_percentage", sa.Float(), nullable=True),
        sa.Column("rank", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["version_id"], ["dataset_versions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_concentration_metrics_dataset_id"), "concentration_metrics", ["dataset_id"], unique=False)
    op.create_index(op.f("ix_concentration_metrics_version_id"), "concentration_metrics", ["version_id"], unique=False)

    # 26. trend_metrics
    op.create_table(
        "trend_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("metric_name", sa.String(length=255), nullable=False),
        sa.Column("period_type", sa.String(length=20), nullable=False),
        sa.Column("period_value", sa.String(length=20), nullable=False),
        sa.Column("metric_value", sa.Float(), nullable=True),
        sa.Column("dimension_name", sa.String(length=100), nullable=True),
        sa.Column("dimension_value", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["version_id"], ["dataset_versions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_trend_metrics_dataset_id"), "trend_metrics", ["dataset_id"], unique=False)
    op.create_index(op.f("ix_trend_metrics_metric_name"), "trend_metrics", ["metric_name"], unique=False)
    op.create_index(op.f("ix_trend_metrics_version_id"), "trend_metrics", ["version_id"], unique=False)

    # 27. risk_migration_cells
    op.create_table(
        "risk_migration_cells",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("from_risk_category", sa.String(length=20), nullable=False),
        sa.Column("to_risk_category", sa.String(length=20), nullable=False),
        sa.Column("borrower_count", sa.Integer(), nullable=True),
        sa.Column("exposure_amount", sa.Float(), nullable=True),
        sa.Column("period_start", sa.Date(), nullable=True),
        sa.Column("period_end", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["version_id"], ["dataset_versions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_risk_migration_cells_dataset_id"), "risk_migration_cells", ["dataset_id"], unique=False)
    op.create_index(op.f("ix_risk_migration_cells_version_id"), "risk_migration_cells", ["version_id"], unique=False)

    # 28. ai_insights
    op.create_table(
        "ai_insights",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("analysis_type", sa.String(length=50), nullable=False),
        sa.Column("executive_summary", sa.Text(), nullable=True),
        sa.Column("key_findings_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("risk_observations_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("recommendations_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("source_metrics_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("provider", sa.String(length=50), nullable=True),
        sa.Column("model_name", sa.String(length=100), nullable=True),
        sa.Column("generated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["generated_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ai_insights_analysis_type"), "ai_insights", ["analysis_type"], unique=False)
    op.create_index(op.f("ix_ai_insights_dataset_id"), "ai_insights", ["dataset_id"], unique=False)

    # 29. reports
    op.create_table(
        "reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("report_type", sa.String(length=60), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("generated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("export_format", sa.String(length=10), nullable=False, server_default="PDF"),
        sa.Column("storage_path", sa.String(length=1024), nullable=True),
        sa.Column("report_metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["generated_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_reports_dataset_id"), "reports", ["dataset_id"], unique=False)
    op.create_index(op.f("ix_reports_report_type"), "reports", ["report_type"], unique=False)

    # 30. system_settings
    op.create_table(
        "system_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("setting_key", sa.String(length=255), nullable=False),
        sa.Column("setting_value", sa.Text(), nullable=True),
        sa.Column("setting_type", sa.String(length=20), nullable=False, server_default="STRING"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_system_settings_setting_key"), "system_settings", ["setting_key"], unique=True)


def downgrade() -> None:
    # Drop FK for active_version_id on datasets first to break circular dependencies
    op.drop_constraint("fk_datasets_active_version_id", "datasets", type_="foreignkey")

    # Drop in exact reverse order
    op.drop_table("system_settings")
    op.drop_table("reports")
    op.drop_table("ai_insights")
    op.drop_table("risk_migration_cells")
    op.drop_table("trend_metrics")
    op.drop_table("concentration_metrics")
    op.drop_table("portfolio_segment_metrics")
    op.drop_table("portfolio_snapshots")
    op.drop_table("risk_driver_breakdowns")
    op.drop_table("risk_assessments")
    op.drop_table("document_analysis_results")
    op.drop_table("document_extractions")
    op.drop_table("documents")
    op.drop_table("column_profiles")
    op.drop_table("profile_runs")
    op.drop_table("validation_issues")
    op.drop_table("validation_runs")
    op.drop_table("loans")
    op.drop_table("borrowers")
    op.drop_table("raw_records")
    op.drop_table("schema_mappings")
    op.drop_table("dataset_columns")
    op.drop_table("dataset_files")
    op.drop_table("dataset_versions")
    op.drop_table("datasets")
    op.drop_table("audit_logs")
    op.drop_table("public_dataset_sources")
    op.drop_table("refresh_tokens")
    op.drop_table("users")
    op.drop_table("roles")
