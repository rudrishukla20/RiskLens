import uuid
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.borrower import Borrower
from app.models.loan import Loan
from app.models.risk_assessment import RiskAssessment


class ConcentrationEngine:
    """
    Deterministic concentration analytics engine computing HHI indexes, segment ranks,
    top borrower exposures, Pareto distributions, and ranked tables.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _get_cat_str(self, cat: Any) -> str:
        if cat is None:
            return "LOW"
        return cat.value if hasattr(cat, "value") else str(cat)

    async def get_metrics(self, dataset_id: uuid.UUID, version_id: uuid.UUID) -> Dict[str, Any]:
        """
        Computes concentration metrics for region, purpose, employment type, income band, and borrowers.
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

        # Query existing risk assessments
        assess_stmt = select(RiskAssessment).where(
            RiskAssessment.dataset_id == dataset_id, RiskAssessment.version_id == version_id
        )
        assess_res = await self.session.execute(assess_stmt)
        assessments_map = {ass.loan_id: ass for ass in assess_res.scalars().all()}

        # Initialize centralized ExposureCalculationService
        from app.services.analytics.exposure_calculation_service import ExposureCalculationService
        exposure_service = ExposureCalculationService(self.session)

        # Call service to get exposures
        total_exposure = await exposure_service.calculate_total_exposure(dataset_id)
        borrower_exposures = await exposure_service.calculate_exposure_by_dimension(dataset_id, "source_borrower_id")
        region_exposures = await exposure_service.calculate_exposure_by_dimension(dataset_id, "region")
        purpose_exposures = await exposure_service.calculate_exposure_by_dimension(dataset_id, "loan_purpose")
        employment_exposures = await exposure_service.calculate_exposure_by_dimension(dataset_id, "employment_type")
        income_exposures = await exposure_service.calculate_exposure_by_dimension(dataset_id, "income_band")

        if total_exposure == 0:
            return self._build_empty_response(dataset_id, version_id)

        # 1. Top Borrower Concentration (Top 10 borrowers)
        top_borrowers = sorted(borrower_exposures.items(), key=lambda x: x[1], reverse=True)[:10]
        top_borrower_sum = sum(val for key, val in top_borrowers)
        top_borrower_pct = round((top_borrower_sum / total_exposure) * 100, 2)

        # Helper to compute HHI and ranked segments lists
        metrics_to_persist = []  # List of dicts representing ConcentrationMetric instances

        hhi_by_dimension = {}
        top_segment_by_dimension = {}

        for dim_name, dim_dict in [
            ("region", region_exposures),
            ("loan_purpose", purpose_exposures),
            ("employment_type", employment_exposures),
            ("income_band", income_exposures),
        ]:
            sorted_items = sorted(dim_dict.items(), key=lambda x: x[1], reverse=True)
            hhi_val = 0.0
            rank = 1
            for key, val in sorted_items:
                # Square the exact unrounded percentage and only round the final HHI sum
                pct_exact = (val / total_exposure) * 100 if total_exposure else 0.0
                hhi_val += pct_exact**2

                pct_display = round(pct_exact, 2)
                metrics_to_persist.append(
                    {
                        "concentration_type": dim_name,
                        "concentration_key": key,
                        "exposure_amount": val,
                        "exposure_percentage": pct_display,
                        "rank": rank,
                    }
                )
                if rank == 1:
                    top_segment_by_dimension[dim_name] = pct_display
                rank += 1
            hhi_by_dimension[dim_name] = round(hhi_val, 2)

        # High-risk concentration: percentage of high-risk loans in top region & purpose segments
        top_region_key = (
            sorted(region_exposures.items(), key=lambda x: x[1], reverse=True)[0][0] if region_exposures else "Unknown Region"
        )
        high_risk_in_top_region = sum(
            float(l.outstanding_amount if l.outstanding_amount is not None else (l.loan_amount or 0.0))
            for l, b in records
            if ((b.region if b else "Unknown Region") or "Unknown Region") == top_region_key
            and assessments_map.get(l.id)
            and self._get_cat_str(assessments_map[l.id].risk_category) == "HIGH"
        )
        total_high_risk_exp = sum(
            float(l.outstanding_amount if l.outstanding_amount is not None else (l.loan_amount or 0.0))
            for l, b in records
            if assessments_map.get(l.id) and self._get_cat_str(assessments_map[l.id].risk_category) == "HIGH"
        )
        high_risk_concentration = (
            round((high_risk_in_top_region / total_high_risk_exp) * 100, 2) if total_high_risk_exp else 0.0
        )

        # Pareto chart (Region segments)
        sorted_regions = sorted(region_exposures.items(), key=lambda x: x[1], reverse=True)
        pareto_regions = []
        cumulative_pct = 0.0
        for reg, exp in sorted_regions:
            pct = (exp / total_exposure) * 100
            cumulative_pct += pct
            pareto_regions.append(
                {
                    "region": reg,
                    "exposure": exp,
                    "percentage": round(pct, 2),
                    "cumulative_percentage": round(cumulative_pct, 2),
                }
            )

        # Treemap payload structure
        regions_list = sorted(list(region_exposures.keys()))
        purposes_list = sorted(list(purpose_exposures.keys()))

        # Region x Purpose cross-tab matrix for Heatmap
        heat_matrix = []
        for reg in regions_list:
            row_vals = []
            for purp in purposes_list:
                cell_exp = sum(
                    float(l.outstanding_amount if l.outstanding_amount is not None else (l.loan_amount or 0.0))
                    for l, b in records
                    if ((b.region if b else "Unknown Region") or "Unknown Region") == reg and l.loan_purpose == purp
                )
                row_vals.append(cell_exp)
            heat_matrix.append(row_vals)

        heatmap = {"regions": regions_list, "purposes": purposes_list, "matrix": heat_matrix}

        # Ranked exposure table combines all segments
        ranked_exposure_table = sorted(metrics_to_persist, key=lambda x: x["exposure_amount"], reverse=True)

        # Build Treemap payload structure with actual children list expected by Recharts Treemap
        treemap_regions = {
            "name": "Total Portfolio",
            "children": [{"name": r, "exposure": e} for r, e in region_exposures.items()]
        }
        treemap_purposes = {
            "name": "Total Portfolio",
            "children": [{"name": p, "exposure": e} for p, e in purpose_exposures.items()]
        }

        return {
            "top_borrower_concentration": top_borrower_pct,
            "top_region_concentration": top_segment_by_dimension.get("region", 0.0),
            "top_loan_purpose_concentration": top_segment_by_dimension.get("loan_purpose", 0.0),
            "top_employment_segment_concentration": top_segment_by_dimension.get("employment_type", 0.0),
            "top_income_band_concentration": top_segment_by_dimension.get("income_band", 0.0),
            "herfindahl_hirschman_index": hhi_by_dimension.get("region", 0.0),
            "hhi_by_dimension": hhi_by_dimension,
            "high_risk_concentration": high_risk_concentration,
            "exposure_concentration": {
                "top_borrowers": [
                    {"borrower_id": b, "exposure": exp, "pct": round((exp / total_exposure) * 100, 2)}
                    for b, exp in top_borrowers
                ],
                "hhi": hhi_by_dimension,
            },
            "metrics_list": metrics_to_persist,  # Helper for service database insertion
            "visualizations": {
                "treemap": {
                    "regions": treemap_regions,
                    "purposes": treemap_purposes,
                },
                "pareto_chart": pareto_regions,
                "heatmap": heatmap,
                "ranked_exposure_table": ranked_exposure_table,
            },
        }

    def _get_income_group(self, income: Optional[float]) -> str:
        if income is None:
            return "Under $30k"
        if income < 30000:
            return "Under $30k"
        if income < 60000:
            return "$30k - $60k"
        if income < 100000:
            return "$60k - $100k"
        if income < 150000:
            return "$100k - $150k"
        return "$150k+"

    def _build_empty_response(self, dataset_id: uuid.UUID, version_id: uuid.UUID) -> Dict[str, Any]:
        return {
            "top_borrower_concentration": 0.0,
            "top_region_concentration": 0.0,
            "top_loan_purpose_concentration": 0.0,
            "top_employment_segment_concentration": 0.0,
            "top_income_band_concentration": 0.0,
            "herfindahl_hirschman_index": 0.0,
            "hhi_by_dimension": {},
            "high_risk_concentration": 0.0,
            "exposure_concentration": {"top_borrowers": [], "hhi": {}},
            "metrics_list": [],
            "visualizations": {
                "treemap": {},
                "pareto_chart": [],
                "heatmap": {"regions": [], "purposes": [], "matrix": []},
                "ranked_exposure_table": [],
            },
        }
