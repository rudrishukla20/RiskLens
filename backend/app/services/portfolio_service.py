import uuid
from datetime import datetime
from typing import Any, Dict

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.concentration_engine import ConcentrationEngine
from app.analytics.migration_engine import MigrationEngine
from app.analytics.portfolio_analytics_engine import PortfolioAnalyticsEngine
from app.analytics.trend_engine import TrendEngine
from app.analytics.vintage_engine import VintageEngine
from app.core.deps import log_audit_action
from app.enums.audit_action import AuditActionEnum
from app.models.concentration_metric import ConcentrationMetric
from app.models.portfolio_segment_metric import PortfolioSegmentMetric
from app.models.portfolio_snapshot import PortfolioSnapshot
from app.models.risk_migration_cell import RiskMigrationCell
from app.models.trend_metric import TrendMetric
from app.models.user import User


class PortfolioService:
    """
    Coordinates calculation and database persistence of the 5 Portfolio Analytics Suite metrics.
    """

    def __init__(self, db: AsyncSession, user: User) -> None:
        self.db = db
        self.user = user

    async def run_portfolio_analysis(self, dataset_id: uuid.UUID, version_id: uuid.UUID) -> Dict[str, Any]:
        """
        Executes and persists the full suite of portfolio, concentration, trend, vintage, and migration analysis.
        """
        # Idempotency cleanup: Clear previous metrics for this dataset version
        await self.db.execute(
            delete(PortfolioSnapshot).where(
                PortfolioSnapshot.dataset_id == dataset_id, PortfolioSnapshot.version_id == version_id
            )
        )
        await self.db.execute(
            delete(PortfolioSegmentMetric).where(
                PortfolioSegmentMetric.dataset_id == dataset_id, PortfolioSegmentMetric.version_id == version_id
            )
        )
        await self.db.execute(
            delete(ConcentrationMetric).where(
                ConcentrationMetric.dataset_id == dataset_id, ConcentrationMetric.version_id == version_id
            )
        )
        await self.db.execute(
            delete(TrendMetric).where(TrendMetric.dataset_id == dataset_id, TrendMetric.version_id == version_id)
        )
        await self.db.execute(
            delete(RiskMigrationCell).where(
                RiskMigrationCell.dataset_id == dataset_id, RiskMigrationCell.version_id == version_id
            )
        )
        await self.db.flush()

        # 1. Run Portfolio Analytics
        port_engine = PortfolioAnalyticsEngine(self.db)
        port_res = await port_engine.get_metrics(dataset_id, version_id)

        # Persist PortfolioSnapshot
        snapshot = PortfolioSnapshot(
            id=uuid.uuid4(),
            dataset_id=dataset_id,
            version_id=version_id,
            portfolio_value=port_res["portfolio_value"],
            total_loans=port_res["total_loans"],
            total_borrowers=port_res["total_borrowers"],
            outstanding_exposure=port_res["outstanding_exposure"],
            high_risk_exposure=port_res["high_risk_exposure"],
            average_risk_score=port_res["average_risk_score"],
            average_loan_size=port_res["average_loan_size"],
            concentration_index=port_res["concentration_index"],
            diversification_index=port_res["diversification_index"],
            snapshot_date=datetime.now().date(),
        )
        self.db.add(snapshot)

        # Persist Segment Slices
        for seg in port_res["segments_list"]:
            db_seg = PortfolioSegmentMetric(
                id=uuid.uuid4(),
                dataset_id=dataset_id,
                version_id=version_id,
                segment_type=seg["segment_type"],
                segment_value=seg["segment_value"],
                borrower_count=seg["borrower_count"],
                loan_count=seg["loan_count"],
                portfolio_value=seg["portfolio_value"],
                outstanding_exposure=seg["outstanding_exposure"],
                average_risk_score=seg["average_risk_score"],
                high_risk_count=seg["high_risk_count"],
                high_risk_exposure=seg["high_risk_exposure"],
            )
            self.db.add(db_seg)

        # 2. Run Concentration Analytics
        con_engine = ConcentrationEngine(self.db)
        con_res = await con_engine.get_metrics(dataset_id, version_id)

        for item in con_res["metrics_list"]:
            db_con = ConcentrationMetric(
                id=uuid.uuid4(),
                dataset_id=dataset_id,
                version_id=version_id,
                concentration_type=item["concentration_type"],
                concentration_key=item["concentration_key"],
                exposure_amount=item["exposure_amount"],
                exposure_percentage=item["exposure_percentage"],
                rank=item["rank"],
            )
            self.db.add(db_con)

        # 3. Run Trend Analytics
        trend_engine = TrendEngine(self.db)
        trend_res = await trend_engine.get_metrics(dataset_id, version_id)

        for item in trend_res["metrics_list"]:
            db_trend = TrendMetric(
                id=uuid.uuid4(),
                dataset_id=dataset_id,
                version_id=version_id,
                metric_name=item["metric_name"],
                period_type=item["period_type"],
                period_value=item["period_value"],
                metric_value=item["metric_value"],
                dimension_name=None,
                dimension_value=None,
            )
            self.db.add(db_trend)

        # 4. Run Vintage Analytics (pure calculation)
        vintage_engine = VintageEngine(self.db)
        vintage_res = await vintage_engine.get_metrics(dataset_id, version_id)

        # 5. Run Risk Migration Analytics
        mig_engine = MigrationEngine(self.db)
        mig_res = await mig_engine.get_metrics(dataset_id, version_id)

        for item in mig_res["cells_list"]:
            db_mig = RiskMigrationCell(
                id=uuid.uuid4(),
                dataset_id=dataset_id,
                version_id=version_id,
                from_risk_category=item["from_risk_category"],
                to_risk_category=item["to_risk_category"],
                borrower_count=item["borrower_count"],
                exposure_amount=item["exposure_amount"],
                period_start=item["period_start"],
                period_end=item["period_end"],
            )
            self.db.add(db_mig)

        await self.db.flush()

        # Audit logging
        await log_audit_action(
            self.db,
            user_id=self.user.id,
            action=AuditActionEnum.ANALYTICS_GENERATED,
            module_name="analytics",
            resource_type="Dataset",
            resource_id=str(dataset_id),
            details={"version_id": str(version_id), "analytics_type": "Portfolio Suite"},
        )

        return {
            "portfolio": port_res,
            "concentration": con_res,
            "trend": trend_res,
            "vintage": vintage_res,
            "migration": mig_res,
        }
