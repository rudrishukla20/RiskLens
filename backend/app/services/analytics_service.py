import logging
import uuid
from typing import Any, Dict

from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.borrower_analytics_engine import BorrowerAnalyticsEngine
from app.analytics.concentration_engine import ConcentrationEngine
from app.analytics.data_quality_engine import DataQualityEngine
from app.analytics.loan_analytics_engine import LoanAnalyticsEngine
from app.analytics.migration_engine import MigrationEngine
from app.analytics.portfolio_analytics_engine import PortfolioAnalyticsEngine
from app.analytics.profiling_engine import ProfilingEngine
from app.analytics.trend_engine import TrendEngine
from app.analytics.vintage_engine import VintageEngine
from app.models.user import User

logger = logging.getLogger(__name__)


class AnalyticsService:
    """
    Service layer for coordinating Credit Risk and Dataset Analytics.
    Wires and exposes the primary deterministic analytics engines.
    """

    def __init__(self, db: AsyncSession, user: User) -> None:
        self.db = db
        self.user = user
        self.data_quality_engine = DataQualityEngine(db)
        self.profiling_engine = ProfilingEngine(db)
        self.borrower_engine = BorrowerAnalyticsEngine(db)
        self.loan_engine = LoanAnalyticsEngine(db)
        self.portfolio_engine = PortfolioAnalyticsEngine(db)
        self.concentration_engine = ConcentrationEngine(db)
        self.trend_engine = TrendEngine(db)
        self.vintage_engine = VintageEngine(db)
        self.migration_engine = MigrationEngine(db)

    async def get_data_quality_analytics(self, dataset_id: uuid.UUID, version_id: uuid.UUID) -> Dict[str, Any]:
        """Runs or retrieves validation run logs and returns quality scorecard metrics."""
        logger.info("Service request: get_data_quality_analytics for version_id=%s", version_id)
        return await self.data_quality_engine.get_metrics(dataset_id, version_id)

    async def get_dataset_profiling(self, dataset_id: uuid.UUID, version_id: uuid.UUID) -> Dict[str, Any]:
        """Runs or retrieves profile runs and returns numerical statistics/correlations."""
        logger.info("Service request: get_dataset_profiling for version_id=%s", version_id)
        return await self.profiling_engine.get_metrics(dataset_id, version_id)

    async def get_borrower_analytics(self, dataset_id: uuid.UUID, version_id: uuid.UUID) -> Dict[str, Any]:
        """Retrieves demographic bands, segment risk, and exposures for borrowers."""
        logger.info("Service request: get_borrower_analytics for version_id=%s", version_id)
        return await self.borrower_engine.get_metrics(dataset_id, version_id)

    async def get_loan_analytics(self, dataset_id: uuid.UUID, version_id: uuid.UUID) -> Dict[str, Any]:
        """Retrieves DPD delinquency buckets, exposure waterfalls, and interest rates for loans."""
        logger.info("Service request: get_loan_analytics for version_id=%s", version_id)
        return await self.loan_engine.get_metrics(dataset_id, version_id)

    async def get_portfolio_analytics(self, dataset_id: uuid.UUID, version_id: uuid.UUID) -> Dict[str, Any]:
        """Retrieves portfolio overall KPIs and exposure segment slices."""
        logger.info("Service request: get_portfolio_analytics for version_id=%s", version_id)
        return await self.portfolio_engine.get_metrics(dataset_id, version_id)

    async def get_concentration_analytics(self, dataset_id: uuid.UUID, version_id: uuid.UUID) -> Dict[str, Any]:
        """Retrieves HHI indexes and exposure segments ranked tables."""
        logger.info("Service request: get_concentration_analytics for version_id=%s", version_id)
        return await self.concentration_engine.get_metrics(dataset_id, version_id)

    async def get_trend_analytics(self, dataset_id: uuid.UUID, version_id: uuid.UUID) -> Dict[str, Any]:
        """Retrieves monthly time-series analytics (growth, exposure, delinquency, risk)."""
        logger.info("Service request: get_trend_analytics for version_id=%s", version_id)
        return await self.trend_engine.get_metrics(dataset_id, version_id)

    async def get_vintage_analytics(self, dataset_id: uuid.UUID, version_id: uuid.UUID) -> Dict[str, Any]:
        """Retrieves cohorted vintage tables and matrices grouped by disbursement quarter."""
        logger.info("Service request: get_vintage_analytics for version_id=%s", version_id)
        return await self.vintage_engine.get_metrics(dataset_id, version_id)

    async def get_migration_analytics(self, dataset_id: uuid.UUID, version_id: uuid.UUID) -> Dict[str, Any]:
        """Retrieves transition count and exposure matrices comparing current version with historical baseline."""
        logger.info("Service request: get_migration_analytics for version_id=%s", version_id)
        return await self.migration_engine.get_metrics(dataset_id, version_id)
