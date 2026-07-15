import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.borrower import Borrower
from app.models.concentration_metric import ConcentrationMetric
from app.models.loan import Loan
from app.models.portfolio_segment_metric import PortfolioSegmentMetric
from app.models.portfolio_snapshot import PortfolioSnapshot
from app.models.risk_assessment import RiskAssessment
from app.models.risk_driver_breakdown import RiskDriverBreakdown
from app.models.risk_migration_cell import RiskMigrationCell
from app.models.trend_metric import TrendMetric
from app.repositories.base import BaseRepository


class AnalyticsRepository(BaseRepository[Borrower]):
    """Repository handling credit risk analytics domain records data access."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Borrower, db)

    # ── Borrowers ─────────────────────────────────────────────────────────────
    async def get_borrowers(self, dataset_id: uuid.UUID) -> List[Borrower]:
        """Queries borrowers records linked to a dataset."""
        stmt = select(Borrower).where(Borrower.dataset_id == dataset_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def bulk_create_borrowers(self, borrowers: List[Borrower]) -> List[Borrower]:
        """Inserts borrower records in bulk."""
        self.db.add_all(borrowers)
        await self.db.flush()
        return borrowers

    # ── Loans ─────────────────────────────────────────────────────────────────
    async def get_loans(self, dataset_id: uuid.UUID) -> List[Loan]:
        """Queries loans records linked to a dataset."""
        stmt = select(Loan).where(Loan.dataset_id == dataset_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def bulk_create_loans(self, loans: List[Loan]) -> List[Loan]:
        """Inserts loan records in bulk."""
        self.db.add_all(loans)
        await self.db.flush()
        return loans

    # ── Risk Assessments ──────────────────────────────────────────────────────
    async def get_risk_assessment_with_drivers(self, assessment_id: uuid.UUID) -> Optional[RiskAssessment]:
        """Queries a risk assessment pre-loading its driver breakdowns."""
        stmt = (
            select(RiskAssessment)
            .where(RiskAssessment.id == assessment_id)
            .options(selectinload(RiskAssessment.driver_breakdowns))
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_risk_assessments(self, dataset_id: uuid.UUID) -> List[RiskAssessment]:
        """Queries risk assessments pre-loading their driver breakdowns."""
        stmt = (
            select(RiskAssessment)
            .where(RiskAssessment.dataset_id == dataset_id)
            .options(selectinload(RiskAssessment.driver_breakdowns))
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def bulk_create_risk_assessments(self, assessments: List[RiskAssessment]) -> List[RiskAssessment]:
        """Inserts risk assessments in bulk."""
        self.db.add_all(assessments)
        await self.db.flush()
        return assessments

    async def bulk_create_driver_breakdowns(self, breakdowns: List[RiskDriverBreakdown]) -> List[RiskDriverBreakdown]:
        """Inserts risk driver explanations in bulk."""
        self.db.add_all(breakdowns)
        await self.db.flush()
        return breakdowns

    # ── Portfolio Snapshots ───────────────────────────────────────────────────
    async def get_latest_portfolio_snapshot(self, dataset_id: uuid.UUID) -> Optional[PortfolioSnapshot]:
        """Queries the latest portfolio summary metrics snapshot."""
        stmt = (
            select(PortfolioSnapshot)
            .where(PortfolioSnapshot.dataset_id == dataset_id)
            .order_by(PortfolioSnapshot.created_at.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def create_portfolio_snapshot(self, snapshot: PortfolioSnapshot) -> PortfolioSnapshot:
        """Saves a new portfolio snapshot summary."""
        self.db.add(snapshot)
        await self.db.flush()
        return snapshot

    # ── Portfolio Segment Metrics ─────────────────────────────────────────────
    async def get_segment_metrics(self, dataset_id: uuid.UUID) -> List[PortfolioSegmentMetric]:
        """Queries cohorted segment metrics classifications."""
        stmt = select(PortfolioSegmentMetric).where(PortfolioSegmentMetric.dataset_id == dataset_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def bulk_create_segment_metrics(self, metrics: List[PortfolioSegmentMetric]) -> List[PortfolioSegmentMetric]:
        """Inserts segment metrics in bulk."""
        self.db.add_all(metrics)
        await self.db.flush()
        return metrics

    # ── Concentration Metrics ─────────────────────────────────────────────────
    async def get_concentration_metrics(self, dataset_id: uuid.UUID) -> List[ConcentrationMetric]:
        """Queries concentration indexes listings."""
        stmt = select(ConcentrationMetric).where(ConcentrationMetric.dataset_id == dataset_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def bulk_create_concentration_metrics(self, metrics: List[ConcentrationMetric]) -> List[ConcentrationMetric]:
        """Inserts concentration metrics in bulk."""
        self.db.add_all(metrics)
        await self.db.flush()
        return metrics

    # ── Trend Metrics ─────────────────────────────────────────────────────────
    async def get_trend_metrics(self, dataset_id: uuid.UUID) -> List[TrendMetric]:
        """Queries metrics trends records."""
        stmt = select(TrendMetric).where(TrendMetric.dataset_id == dataset_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def bulk_create_trend_metrics(self, metrics: List[TrendMetric]) -> List[TrendMetric]:
        """Inserts trend metrics in bulk."""
        self.db.add_all(metrics)
        await self.db.flush()
        return metrics

    # ── Risk Migration Cells ──────────────────────────────────────────────────
    async def get_migration_cells(self, dataset_id: uuid.UUID) -> List[RiskMigrationCell]:
        """Queries cohorted risk migration transition records."""
        stmt = select(RiskMigrationCell).where(RiskMigrationCell.dataset_id == dataset_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def bulk_create_migration_cells(self, cells: List[RiskMigrationCell]) -> List[RiskMigrationCell]:
        """Inserts transition cell logs in bulk."""
        self.db.add_all(cells)
        await self.db.flush()
        return cells
