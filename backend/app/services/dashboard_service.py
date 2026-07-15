from typing import Any, Dict

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums.user_status import UserStatusEnum
from app.models.audit_log import AuditLog
from app.models.dataset import Dataset
from app.models.dataset_file import DatasetFile
from app.models.user import User


class DashboardService:
    """Service generating aggregated tiles metrics for dashboards."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_admin_dashboard_data(self) -> Dict[str, Any]:
        """Compiles system administrative metrics for platform monitors."""
        # 1. Total users
        stmt_tot_users = select(func.count(User.id))
        res_tot_users = await self.db.execute(stmt_tot_users)
        total_users = res_tot_users.scalar() or 0

        # 2. Active users
        stmt_act_users = select(func.count(User.id)).where(User.status == UserStatusEnum.ACTIVE)
        res_act_users = await self.db.execute(stmt_act_users)
        active_users = res_act_users.scalar() or 0

        # 3. Total datasets
        stmt_tot_ds = select(func.count(Dataset.id))
        res_tot_ds = await self.db.execute(stmt_tot_ds)
        total_datasets = res_tot_ds.scalar() or 0

        # 4. Total storage
        stmt_storage = select(func.sum(DatasetFile.file_size_bytes))
        res_storage = await self.db.execute(stmt_storage)
        total_storage = res_storage.scalar() or 0

        # 5. Recent audit logs (limit 10)
        stmt_audits = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(10)
        res_audits = await self.db.execute(stmt_audits)
        recent_audits = []
        for log in res_audits.scalars().all():
            action_str = log.action.value if hasattr(log.action, "value") else str(log.action)
            recent_audits.append(
                {
                    "id": str(log.id),
                    "action": action_str,
                    "user_id": str(log.user_id) if log.user_id else None,
                    "created_at": log.created_at.isoformat(),
                }
            )

        return {
            "system_metrics": {
                "total_users_count": total_users,
                "active_users_count": active_users,
                "total_datasets_uploaded": total_datasets,
                "storage_used_bytes": total_storage,
                "system_load_status": "HEALTHY",
            },
            "recent_activity_logs": recent_audits,
        }

    async def get_risk_dashboard_data(self) -> Dict[str, Any]:
        """
        Calculates cohorted credit portfolio metrics.
        Queries the database for the active snapshot and segments.
        """
        # Resolve the latest active dataset
        dataset_stmt = select(Dataset).where(Dataset.archived_at.is_(None)).order_by(Dataset.created_at.desc()).limit(1)
        res_dataset = await self.db.execute(dataset_stmt)
        dataset = res_dataset.scalar_one_or_none()

        if not dataset or not dataset.active_version_id:
            return {
                "total_portfolio_exposure": 0.0,
                "weighted_average_risk_score": 0.0,
                "total_delinquency_exposure": 0.0,
                "delinquent_loans_count": 0,
                "risk_distribution": {
                    "low_risk_count": 0,
                    "medium_risk_count": 0,
                    "high_risk_count": 0,
                    "low_risk_exposure": 0.0,
                    "medium_risk_exposure": 0.0,
                    "high_risk_exposure": 0.0,
                },
                "recent_risk_trends": [],
                "sector_concentration": [],
            }

        # Query latest PortfolioSnapshot for average risk (exposure will be calculated by centralized service)
        from app.models.portfolio_snapshot import PortfolioSnapshot
        snapshot_stmt = select(PortfolioSnapshot).where(
            PortfolioSnapshot.dataset_id == dataset.id,
            PortfolioSnapshot.version_id == dataset.active_version_id
        ).order_by(PortfolioSnapshot.created_at.desc()).limit(1)
        res_snapshot = await self.db.execute(snapshot_stmt)
        snapshot = res_snapshot.scalar_one_or_none()

        weighted_average_risk_score = float(snapshot.average_risk_score or 0.0) if snapshot else 0.0

        # Import and initialize ExposureCalculationService
        from app.services.analytics.exposure_calculation_service import ExposureCalculationService
        exposure_service = ExposureCalculationService(self.db)

        # Calculate total portfolio exposure using the centralized service
        total_portfolio_exposure = await exposure_service.calculate_total_exposure(dataset.id)

        # Query delinquent metrics
        # Count delinquent loans directly from Loan table (DPD > 30)
        from app.models.loan import Loan
        delinq_count_stmt = select(func.count(Loan.id)).where(
            Loan.dataset_id == dataset.id,
            Loan.version_id == dataset.active_version_id,
            Loan.delinquency_days > 30
        )
        delinquent_loans_count = (await self.db.execute(delinq_count_stmt)).scalar() or 0

        # Calculate delinquency exposure using the centralized service with range filter
        total_delinquency_exposure = await exposure_service.calculate_total_exposure(
            dataset.id,
            filters={"delinquency_days": ("gt", 30)}
        )

        # Query risk category distribution metrics using the centralized service
        from app.models.risk_assessment import RiskAssessment

        # 1. Query counts grouped by risk category
        count_stmt = select(
            RiskAssessment.risk_category,
            func.count(RiskAssessment.id)
        ).where(
            RiskAssessment.dataset_id == dataset.id,
            RiskAssessment.version_id == dataset.active_version_id
        ).group_by(RiskAssessment.risk_category)
        res_counts = await self.db.execute(count_stmt)

        counts_map = {}
        for row in res_counts.all():
            cat = row[0]
            cat_str = cat.value if hasattr(cat, "value") else str(cat)
            counts_map[cat_str] = int(row[1] or 0)

        # 2. Query exposures by risk category using the centralized service
        risk_exposures = await exposure_service.calculate_exposure_by_dimension(dataset.id, "risk_category")

        risk_dist = {
            "low_risk_count": counts_map.get("LOW", 0),
            "medium_risk_count": counts_map.get("MEDIUM", 0),
            "high_risk_count": counts_map.get("HIGH", 0),
            "low_risk_exposure": float(risk_exposures.get("LOW", 0.0)),
            "medium_risk_exposure": float(risk_exposures.get("MEDIUM", 0.0)),
            "high_risk_exposure": float(risk_exposures.get("HIGH", 0.0)),
        }

        # Query recent risk trends from TrendMetric
        from app.models.trend_metric import TrendMetric
        trends_stmt = select(TrendMetric).where(
            TrendMetric.dataset_id == dataset.id,
            TrendMetric.version_id == dataset.active_version_id,
            TrendMetric.metric_name == "average_risk_score"
        ).order_by(TrendMetric.period_value.asc())
        res_trends = await self.db.execute(trends_stmt)
        recent_risk_trends = [
            {"period": t.period_value, "average_risk_score": float(t.metric_value or 0.0)}
            for t in res_trends.scalars().all()
        ]

        # Query sector concentration from PortfolioSegmentMetric
        from app.models.portfolio_segment_metric import PortfolioSegmentMetric
        sectors_stmt = select(PortfolioSegmentMetric).where(
            PortfolioSegmentMetric.dataset_id == dataset.id,
            PortfolioSegmentMetric.version_id == dataset.active_version_id,
            PortfolioSegmentMetric.segment_type == "loan_purpose"
        ).order_by(PortfolioSegmentMetric.outstanding_exposure.desc())
        res_sectors = await self.db.execute(sectors_stmt)
        sector_concentration = [
            {
                "sector": s.segment_value,
                "loans_count": int(s.loan_count or 0),
                "exposure_amount": float(s.outstanding_exposure or 0.0),
                "average_risk_score": float(s.average_risk_score or 0.0)
            }
            for s in res_sectors.scalars().all()
        ]

        return {
            "total_portfolio_exposure": total_portfolio_exposure,
            "weighted_average_risk_score": weighted_average_risk_score,
            "total_delinquency_exposure": total_delinquency_exposure,
            "delinquent_loans_count": delinquent_loans_count,
            "risk_distribution": risk_dist,
            "recent_risk_trends": recent_risk_trends,
            "sector_concentration": sector_concentration,
        }
