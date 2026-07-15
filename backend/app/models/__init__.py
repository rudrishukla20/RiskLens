"""
ORM model registry — Complete (Part 1 + Part 2).

Importing all models here ensures SQLAlchemy's mapper registry is fully
populated before Alembic autogenerate or any table-creation call.
"""

# ── AI insights ───────────────────────────────────────────────────────────────
from app.models.ai_insight import AIInsight  # noqa: F401
from app.models.audit_log import AuditLog  # noqa: F401
from app.models.base import Base  # noqa: F401

# ── Canonical domain entities ─────────────────────────────────────────────────
from app.models.borrower import Borrower  # noqa: F401
from app.models.column_profile import ColumnProfile  # noqa: F401
from app.models.concentration_metric import ConcentrationMetric  # noqa: F401

# ── Dataset ingestion ─────────────────────────────────────────────────────────
from app.models.dataset import Dataset  # noqa: F401
from app.models.dataset_column import DatasetColumn  # noqa: F401
from app.models.dataset_file import DatasetFile  # noqa: F401
from app.models.dataset_version import DatasetVersion  # noqa: F401

# ── Documents ─────────────────────────────────────────────────────────────────
from app.models.document import Document  # noqa: F401
from app.models.document_analysis_result import DocumentAnalysisResult  # noqa: F401
from app.models.document_extraction import DocumentExtraction  # noqa: F401
from app.models.loan import Loan  # noqa: F401
from app.models.portfolio_segment_metric import PortfolioSegmentMetric  # noqa: F401

# ── Portfolio analytics ───────────────────────────────────────────────────────
from app.models.portfolio_snapshot import PortfolioSnapshot  # noqa: F401

# ── Profiling ─────────────────────────────────────────────────────────────────
from app.models.profiling import ProfileRun  # noqa: F401

# ── Reference & admin ─────────────────────────────────────────────────────────
from app.models.public_dataset_source import PublicDatasetSource  # noqa: F401

# ── Raw records ───────────────────────────────────────────────────────────────
from app.models.raw_record import RawRecord  # noqa: F401
from app.models.refresh_token import RefreshToken  # noqa: F401

# ── Reports ───────────────────────────────────────────────────────────────────
from app.models.report import Report  # noqa: F401

# ── Risk assessment ───────────────────────────────────────────────────────────
from app.models.risk_assessment import RiskAssessment  # noqa: F401
from app.models.risk_driver_breakdown import RiskDriverBreakdown  # noqa: F401
from app.models.risk_migration_cell import RiskMigrationCell  # noqa: F401

# ── Auth & IAM ────────────────────────────────────────────────────────────────
from app.models.role import Role  # noqa: F401

# ── Schema mapping ────────────────────────────────────────────────────────────
from app.models.schema_mapping import SchemaMapping  # noqa: F401
from app.models.system_setting import SystemSetting  # noqa: F401
from app.models.trend_metric import TrendMetric  # noqa: F401
from app.models.user import User  # noqa: F401

# ── Validation ────────────────────────────────────────────────────────────────
from app.models.validation import ValidationRun  # noqa: F401
from app.models.validation_issue import ValidationIssue  # noqa: F401

__all__ = [
    "Base",
    # Auth & IAM
    "Role",
    "User",
    "RefreshToken",
    # Dataset ingestion
    "Dataset",
    "DatasetVersion",
    "DatasetFile",
    "DatasetColumn",
    # Schema mapping
    "SchemaMapping",
    # Raw records
    "RawRecord",
    # Canonical domain
    "Borrower",
    "Loan",
    # Validation
    "ValidationRun",
    "ValidationIssue",
    # Profiling
    "ProfileRun",
    "ColumnProfile",
    # Documents
    "Document",
    "DocumentExtraction",
    "DocumentAnalysisResult",
    # Risk
    "RiskAssessment",
    "RiskDriverBreakdown",
    # Portfolio analytics
    "PortfolioSnapshot",
    "PortfolioSegmentMetric",
    "ConcentrationMetric",
    "TrendMetric",
    "RiskMigrationCell",
    # AI insights
    "AIInsight",
    # Reports
    "Report",
    # Reference & admin
    "PublicDatasetSource",
    "SystemSetting",
    "AuditLog",
]
