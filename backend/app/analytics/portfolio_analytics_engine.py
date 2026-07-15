import uuid
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.borrower import Borrower
from app.models.loan import Loan
from app.models.risk_assessment import RiskAssessment


class PortfolioAnalyticsEngine:
    """
    Deterministic analytics engine for computing overall portfolio indicators,
    segment exposures, concentration indices, and KPI distributions.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _get_cat_str(self, cat: Any) -> str:
        if cat is None:
            return "LOW"
        return cat.value if hasattr(cat, "value") else str(cat)

    async def get_metrics(self, dataset_id: uuid.UUID, version_id: uuid.UUID) -> Dict[str, Any]:
        """
        Computes portfolio-wide and segment-sliced exposure metrics for the dataset version.
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

        total_loans = len(records)
        borrower_ids = set()
        portfolio_value = 0.0
        risk_scores = []

        # Initialize centralized ExposureCalculationService
        from app.services.analytics.exposure_calculation_service import ExposureCalculationService
        exposure_service = ExposureCalculationService(self.session)

        # CENTRALIZED EXPOSURE CALLS
        outstanding_exposure = await exposure_service.calculate_total_exposure(dataset_id)
        region_exposure = await exposure_service.calculate_exposure_by_dimension(dataset_id, "region")
        purpose_exposure = await exposure_service.calculate_exposure_by_dimension(dataset_id, "loan_purpose")
        employment_exposure = await exposure_service.calculate_exposure_by_dimension(dataset_id, "employment_type")
        income_exposure = await exposure_service.calculate_exposure_by_dimension(dataset_id, "income_band")

        risk_exposures = await exposure_service.calculate_exposure_by_dimension(dataset_id, "risk_category")
        high_risk_exposure = float(risk_exposures.get("HIGH", 0.0))

        # Segment collections
        segment_details = {
            "region": {},
            "loan_purpose": {},
            "employment_type": {},
            "income_band": {
                "Under $30k": {
                    "borrowers": set(),
                    "loans": 0,
                    "val": 0.0,
                    "exp": 0.0,
                    "risk_scores": [],
                    "high_risk_count": 0,
                    "high_risk_exp": 0.0,
                },
                "$30k - $60k": {
                    "borrowers": set(),
                    "loans": 0,
                    "val": 0.0,
                    "exp": 0.0,
                    "risk_scores": [],
                    "high_risk_count": 0,
                    "high_risk_exp": 0.0,
                },
                "$60k - $100k": {
                    "borrowers": set(),
                    "loans": 0,
                    "val": 0.0,
                    "exp": 0.0,
                    "risk_scores": [],
                    "high_risk_count": 0,
                    "high_risk_exp": 0.0,
                },
                "$100k - $150k": {
                    "borrowers": set(),
                    "loans": 0,
                    "val": 0.0,
                    "exp": 0.0,
                    "risk_scores": [],
                    "high_risk_count": 0,
                    "high_risk_exp": 0.0,
                },
                "$150k+": {
                    "borrowers": set(),
                    "loans": 0,
                    "val": 0.0,
                    "exp": 0.0,
                    "risk_scores": [],
                    "high_risk_count": 0,
                    "high_risk_exp": 0.0,
                },
            },
        }

        for loan, borrower in records:
            b_id = borrower.id if borrower else None
            if b_id:
                borrower_ids.add(b_id)

            loan_val = float(loan.loan_amount or 0.0)
            loan_exp = float(loan.outstanding_amount if loan.outstanding_amount is not None else (loan.loan_amount or 0.0))
            portfolio_value += loan_val

            # Resolve risk details
            ass = assessments_map.get(loan.id)
            score = ass.risk_score if ass else 0.0
            category = self._get_cat_str(ass.risk_category) if ass else "LOW"
            risk_scores.append(score)

            is_high_risk = category == "HIGH"

            # Helpers for segments aggregation
            region = borrower.region if borrower else None
            if not region or region in ("Unknown", "N/A", "None", ""):
                region = "Unknown Region"
            purpose = loan.loan_purpose or "Unknown"
            employment = (borrower.employment_type if borrower else "Unknown") or "Unknown"

            income = borrower.income if borrower else None
            income_grp = self._get_income_group(income)

            # Collect metrics per segment type
            for seg_type, seg_val in [
                ("region", region),
                ("loan_purpose", purpose),
                ("employment_type", employment),
                ("income_band", income_grp),
            ]:
                if seg_type == "income_band":
                    seg_dict = segment_details[seg_type][seg_val]
                else:
                    if seg_val not in segment_details[seg_type]:
                        segment_details[seg_type][seg_val] = {
                            "borrowers": set(),
                            "loans": 0,
                            "val": 0.0,
                            "exp": 0.0,
                            "risk_scores": [],
                            "high_risk_count": 0,
                            "high_risk_exp": 0.0,
                        }
                    seg_dict = segment_details[seg_type][seg_val]

                if b_id:
                    seg_dict["borrowers"].add(b_id)
                seg_dict["loans"] += 1
                seg_dict["val"] += loan_val
                seg_dict["exp"] += loan_exp
                seg_dict["risk_scores"].append(score)
                if is_high_risk:
                    seg_dict["high_risk_count"] += 1
                    seg_dict["high_risk_exp"] += loan_exp

        total_borrowers = len(borrower_ids)
        avg_loan_size = round(portfolio_value / total_loans, 2) if total_loans else 0.0
        avg_risk_score = round(sum(risk_scores) / len(risk_scores), 2) if risk_scores else 0.0
        high_risk_percentage = (
            round((high_risk_exposure / outstanding_exposure) * 100, 2) if outstanding_exposure else 0.0
        )

        # Calculate HHI (Herfindahl-Hirschman Index) on region exposure
        hhi = 0.0
        if outstanding_exposure > 0:
            for reg, exp in region_exposure.items():
                pct = (exp / outstanding_exposure) * 100
                hhi += pct**2

        concentration_index = round(hhi / 10000.0, 4)
        diversification_index = round(1.0 - concentration_index, 4)

        # Build segments list to return
        segments_summary = []
        all_segments_list = []
        for seg_type in segment_details:
            for seg_val, details in segment_details[seg_type].items():
                seg_avg_score = (
                    round(sum(details["risk_scores"]) / len(details["risk_scores"]), 2)
                    if details["risk_scores"]
                    else 0.0
                )
                all_segments_list.append(
                    {
                        "segment_type": seg_type,
                        "segment_value": seg_val,
                        "borrower_count": len(details["borrowers"]),
                        "loan_count": details["loans"],
                        "portfolio_value": details["val"],
                        "outstanding_exposure": details["exp"],
                        "average_risk_score": seg_avg_score,
                        "high_risk_count": details["high_risk_count"],
                        "high_risk_exposure": details["high_risk_exp"],
                    }
                )

        # Top 10 exposure segments & high risk segments
        top_exposure_segments = sorted(all_segments_list, key=lambda x: x["outstanding_exposure"], reverse=True)[:10]
        top_high_risk_segments = sorted(all_segments_list, key=lambda x: x["high_risk_exposure"], reverse=True)[:10]

        # Donut viz (Low, Med, High exposure)
        donut_counts = {
            "LOW": float(risk_exposures.get("LOW", 0.0)),
            "MEDIUM": float(risk_exposures.get("MEDIUM", 0.0)),
            "HIGH": float(risk_exposures.get("HIGH", 0.0)),
        }

        donut_viz = {
            cat: {
                "exposure": val,
                "percentage": round((val / outstanding_exposure) * 100, 2) if outstanding_exposure else 0.0,
            }
            for cat, val in donut_counts.items()
        }

        # Heatmaps and matrices
        regions_list = sorted(list(region_exposure.keys()))
        purposes_list = sorted(list(purpose_exposure.keys()))

        # Region x Purpose exposure matrix
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

        concentration_heatmap = {"regions": regions_list, "purposes": purposes_list, "matrix": heat_matrix}

        # Region x Risk Category exposure matrix (flattens to objects for the frontend list map)
        region_risk_matrix = []
        for reg in regions_list:
            for cat in ["LOW", "MEDIUM", "HIGH"]:
                matching_records = [
                    (l, b) for l, b in records
                    if ((b.region if b else "Unknown Region") or "Unknown Region") == reg
                    and (self._get_cat_str(assessments_map[l.id].risk_category) if l.id in assessments_map else "LOW") == cat
                ]
                cell_exp = sum(
                    float(l.outstanding_amount if l.outstanding_amount is not None else (l.loan_amount or 0.0))
                    for l, b in matching_records
                )
                region_risk_matrix.append({
                    "region": reg,
                    "risk_category": cat,
                    "count": len(matching_records),
                    "exposure": round(cell_exp, 2)
                })

        region_risk_heatmap = {
            "regions": regions_list,
            "risk_categories": ["LOW", "MEDIUM", "HIGH"],
            "matrix": region_risk_matrix,
        }

        return {
            "portfolio_value": portfolio_value,
            "outstanding_exposure": outstanding_exposure,
            "total_loans": total_loans,
            "total_borrowers": total_borrowers,
            "average_loan_size": avg_loan_size,
            "average_risk_score": avg_risk_score,
            "high_risk_exposure": high_risk_exposure,
            "high_risk_exposure_percentage": high_risk_percentage,
            "concentration_index": concentration_index,
            "diversification_index": diversification_index,
            "top_10_exposure_segments": top_exposure_segments,
            "top_10_high_risk_segments": top_high_risk_segments,
            "segments_list": all_segments_list,  # helper for service persistence
            "visualizations": {
                "portfolio_kpi_cards": {
                    "total_portfolio_value": portfolio_value,
                    "outstanding_exposure": outstanding_exposure,
                    "active_loans": total_loans,
                    "unique_borrowers": total_borrowers,
                    "avg_loan_size": avg_loan_size,
                    "avg_risk_score": avg_risk_score,
                    "high_risk_exposure": high_risk_exposure,
                    "high_risk_exposure_percentage": high_risk_percentage,
                },
                "exposure_distribution": {
                    "regions": region_exposure,
                    "loan_purposes": purpose_exposure,
                    "employment_types": employment_exposure,
                    "income_bands": income_exposure,
                },
                "portfolio_composition_donut": donut_viz,
                "exposure_treemap": {
                    "regions": {
                        r: round((e / outstanding_exposure) * 100, 2) if outstanding_exposure else 0.0
                        for r, e in region_exposure.items()
                    },
                    "purposes": {
                        p: round((e / outstanding_exposure) * 100, 2) if outstanding_exposure else 0.0
                        for p, e in purpose_exposure.items()
                    },
                },
                "concentration_heatmap": concentration_heatmap,
                "top_concentration_table": top_exposure_segments[:5],
                "region_risk_heatmap": region_risk_heatmap,
                "segment_drilldown_table": all_segments_list,
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
            "portfolio_value": 0.0,
            "outstanding_exposure": 0.0,
            "total_loans": 0,
            "total_borrowers": 0,
            "average_loan_size": 0.0,
            "average_risk_score": 0.0,
            "high_risk_exposure": 0.0,
            "high_risk_exposure_percentage": 0.0,
            "concentration_index": 0.0,
            "diversification_index": 1.0,
            "top_10_exposure_segments": [],
            "top_10_high_risk_segments": [],
            "segments_list": [],
            "visualizations": {
                "portfolio_kpi_cards": {},
                "exposure_distribution": {},
                "portfolio_composition_donut": {},
                "exposure_treemap": {},
                "concentration_heatmap": {"regions": [], "purposes": [], "matrix": []},
                "top_concentration_table": [],
                "region_risk_heatmap": {"regions": [], "risk_categories": [], "matrix": []},
                "segment_drilldown_table": [],
            },
        }
