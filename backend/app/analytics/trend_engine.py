import uuid
from typing import Any, Dict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.borrower import Borrower
from app.models.loan import Loan
from app.models.risk_assessment import RiskAssessment


class TrendEngine:
    """
    Deterministic trend analytics engine that processes date-based time series.
    Safely handles missing or partial date parameters without raising exceptions.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _get_cat_str(self, cat: Any) -> str:
        if cat is None:
            return "LOW"
        return cat.value if hasattr(cat, "value") else str(cat)

    async def get_metrics(self, dataset_id: uuid.UUID, version_id: uuid.UUID) -> Dict[str, Any]:
        """
        Groups loans by disbursement month to generate historical growth, exposure, and risk trend metrics.
        """
        # Query loans and left-joined borrowers
        stmt = (
            select(Loan, Borrower)
            .join(Borrower, Loan.borrower_id == Borrower.id, isouter=True)
            .where(Loan.dataset_id == dataset_id, Loan.version_id == version_id)
        )
        result = await self.session.execute(stmt)
        records = result.all()

        if not records:
            return self._build_empty_response(dataset_id, version_id)

        # Check date availability (excluding synthetic ones)
        has_dates = any(
            loan.disbursement_date is not None and not (
                loan.additional_attributes_json and loan.additional_attributes_json.get("date_is_synthetic")
            )
            for loan, borrower in records
        )
        if not has_dates:
            return {
                "status": "unavailable",
                "message": "unavailable: disbursement date field not found or completely missing",
                "metrics_list": [],
                "visualizations": {
                    "loan_growth_line": [],
                    "exposure_trend_area": [],
                    "risk_score_trend_line": [],
                    "delinquency_trend_line": [],
                },
            }

        # Query existing risk assessments
        assess_stmt = select(RiskAssessment).where(
            RiskAssessment.dataset_id == dataset_id, RiskAssessment.version_id == version_id
        )
        assess_res = await self.session.execute(assess_stmt)
        assessments_map = {ass.loan_id: ass for ass in assess_res.scalars().all()}

        # Group by disbursement month ("YYYY-MM")
        grouped_data = {}
        for loan, borrower in records:
            d_date = loan.disbursement_date
            if not d_date:
                continue
            # Exclude records with synthetic dates from historical trends
            if loan.additional_attributes_json and loan.additional_attributes_json.get("date_is_synthetic"):
                continue
            month_str = d_date.strftime("%Y-%m")
            if month_str not in grouped_data:
                grouped_data[month_str] = []
            grouped_data[month_str].append((loan, borrower))

        # Sort months chronologically
        sorted_months = sorted(grouped_data.keys())

        metrics_to_persist = []
        loan_growth_line = []
        exposure_trend_area = []
        risk_score_trend_line = []
        delinquency_trend_line = []

        cumulative_loans = 0
        cumulative_volume = 0.0

        for month in sorted_months:
            month_records = grouped_data[month]

            monthly_loans = len(month_records)
            monthly_volume = sum(l.loan_amount or 0.0 for l, b in month_records)
            monthly_exposure = sum(l.outstanding_amount or 0.0 for l, b in month_records)

            monthly_risk_scores = [
                assessments_map[l.id].risk_score for l, b in month_records if l.id in assessments_map
            ]
            avg_risk = round(sum(monthly_risk_scores) / len(monthly_risk_scores), 2) if monthly_risk_scores else 0.0

            high_risk_exp = sum(
                l.outstanding_amount or 0.0
                for l, b in month_records
                if l.id in assessments_map and self._get_cat_str(assessments_map[l.id].risk_category) == "HIGH"
            )

            monthly_delinquencies = [l.delinquency_days for l, b in month_records if l.delinquency_days is not None]
            avg_delinquency = (
                round(sum(monthly_delinquencies) / len(monthly_delinquencies), 2) if monthly_delinquencies else 0.0
            )

            cumulative_loans += monthly_loans
            cumulative_volume += monthly_volume

            # Add to visualization datasets
            loan_growth_line.append(
                {
                    "period": month,
                    "monthly_count": monthly_loans,
                    "monthly_volume": monthly_volume,
                    "cumulative_count": cumulative_loans,
                    "cumulative_volume": cumulative_volume,
                }
            )
            exposure_trend_area.append(
                {"period": month, "exposure": monthly_exposure, "high_risk_exposure": high_risk_exp}
            )
            risk_score_trend_line.append({"period": month, "average_risk_score": avg_risk})
            delinquency_trend_line.append({"period": month, "average_delinquency_days": avg_delinquency})

            # Prepare DB models metadata
            for m_name, m_val in [
                ("loan_count", float(monthly_loans)),
                ("loan_volume", monthly_volume),
                ("outstanding_exposure", monthly_exposure),
                ("average_risk_score", avg_risk),
                ("high_risk_exposure", high_risk_exp),
                ("average_delinquency_days", avg_delinquency),
            ]:
                metrics_to_persist.append(
                    {"metric_name": m_name, "period_type": "MONTHLY", "period_value": month, "metric_value": m_val}
                )

        return {
            "status": "success",
            "metrics_list": metrics_to_persist,  # Helper for service database insertion
            "visualizations": {
                "loan_growth_line": loan_growth_line,
                "exposure_trend_area": exposure_trend_area,
                "risk_score_trend_line": risk_score_trend_line,
                "delinquency_trend_line": delinquency_trend_line,
            },
        }

    def _build_empty_response(self, dataset_id: uuid.UUID, version_id: uuid.UUID) -> Dict[str, Any]:
        return {
            "status": "unavailable",
            "message": "unavailable: dataset is empty",
            "metrics_list": [],
            "visualizations": {
                "loan_growth_line": [],
                "exposure_trend_area": [],
                "risk_score_trend_line": [],
                "delinquency_trend_line": [],
            },
        }
