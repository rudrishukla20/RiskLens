import uuid
from typing import Any, Dict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.borrower import Borrower
from app.models.loan import Loan
from app.models.risk_assessment import RiskAssessment
from app.models.risk_driver_breakdown import RiskDriverBreakdown
from app.utils.statistics import calculate_correlation_matrix, calculate_mean, calculate_std_dev


class DiagnosticEngine:
    """
    Consolidated diagnostic analytics engine performing segment comparisons,
    correlation analysis, anomaly detection, and root-cause analysis.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _get_cat_str(self, cat: Any) -> str:
        if cat is None:
            return "LOW"
        return cat.value if hasattr(cat, "value") else str(cat)

    async def get_metrics(self, dataset_id: uuid.UUID, version_id: uuid.UUID) -> Dict[str, Any]:
        """
        Gathers risk assessments, loans, and borrowers to formulate correlation matrices and root-cause insights.
        """
        # Query loans and left-joined borrowers
        stmt = (
            select(Loan, Borrower)
            .join(Borrower, Loan.borrower_id == Borrower.id, isouter=True)
            .where(Loan.dataset_id == dataset_id, Loan.version_id == version_id)
        )
        records = (await self.session.execute(stmt)).all()

        if not records:
            return self._build_empty_response(dataset_id, version_id)

        # Query risk assessments
        assess_stmt = select(RiskAssessment).where(
            RiskAssessment.dataset_id == dataset_id, RiskAssessment.version_id == version_id
        )
        assessments = list((await self.session.execute(assess_stmt)).scalars().all())
        assessments_map = {ass.loan_id: ass for ass in assessments}

        # Query driver breakdowns
        assess_ids = [ass.id for ass in assessments]
        driver_breakdowns_map = {}
        if assess_ids:
            driver_stmt = select(RiskDriverBreakdown).where(RiskDriverBreakdown.risk_assessment_id.in_(assess_ids))
            drivers_res = await self.session.execute(driver_stmt)
            for db_br in drivers_res.scalars().all():
                if db_br.risk_assessment_id not in driver_breakdowns_map:
                    driver_breakdowns_map[db_br.risk_assessment_id] = []
                driver_breakdowns_map[db_br.risk_assessment_id].append(db_br)

        # 1. Segment Slicing Comparisons
        segments = {"region": {}, "loan_purpose": {}, "employment_type": {}}

        driver_names = set()
        overall_delinquencies = []
        overall_incomes = []

        for loan, borrower in records:
            b_id = borrower.id if borrower else None
            region = (borrower.region if borrower else "N/A") or "N/A"
            purpose = loan.loan_purpose or "N/A"
            employment = (borrower.employment_type if borrower else "N/A") or "N/A"

            exp = loan.outstanding_amount or 0.0
            loan_val = loan.loan_amount or 0.0
            del_days = loan.delinquency_days or 0.0
            income = borrower.income if borrower else 0.0

            overall_delinquencies.append(del_days)
            if borrower and borrower.income is not None:
                overall_incomes.append(borrower.income)

            ass = assessments_map.get(loan.id)
            score = ass.risk_score if ass else 0.0
            cat_str = self._get_cat_str(ass.risk_category) if ass else "LOW"
            is_high = cat_str == "HIGH"

            # Get drivers for root cause analysis
            drivers_list = driver_breakdowns_map.get(ass.id, []) if ass else []
            for d in drivers_list:
                driver_names.add(d.driver_name)

            for seg_type, seg_val in [("region", region), ("loan_purpose", purpose), ("employment_type", employment)]:
                if seg_val not in segments[seg_type]:
                    segments[seg_type][seg_val] = {
                        "loans_count": 0,
                        "exposure": 0.0,
                        "risk_scores": [],
                        "high_risk_count": 0,
                        "high_risk_exp": 0.0,
                        "delinquencies": [],
                        "incomes": [],
                        "driver_contribs": {},
                    }
                sd = segments[seg_type][seg_val]
                sd["loans_count"] += 1
                sd["exposure"] += exp
                sd["risk_scores"].append(score)
                sd["delinquencies"].append(del_days)
                if borrower and borrower.income is not None:
                    sd["incomes"].append(borrower.income)
                if is_high:
                    sd["high_risk_count"] += 1
                    sd["high_risk_exp"] += exp

                # Add driver contributions for this segment
                for d in drivers_list:
                    if d.driver_name not in sd["driver_contribs"]:
                        sd["driver_contribs"][d.driver_name] = []
                    sd["driver_contribs"][d.driver_name].append(d.contribution_score or 0.0)

        # Build Segment Comparison list
        segment_comparison_table = []
        highest_risk_segment = None
        highest_risk_score = -1.0
        highest_risk_type = ""

        for seg_type in segments:
            for seg_val, sd in segments[seg_type].items():
                avg_risk = round(calculate_mean(sd["risk_scores"]), 2) if sd["risk_scores"] else 0.0
                avg_del = round(calculate_mean(sd["delinquencies"]), 2) if sd["delinquencies"] else 0.0
                avg_inc = round(calculate_mean(sd["incomes"]), 2) if sd["incomes"] else 0.0

                segment_comparison_table.append(
                    {
                        "segment_type": seg_type,
                        "segment_value": seg_val,
                        "loans_count": sd["loans_count"],
                        "outstanding_exposure": sd["exposure"],
                        "average_risk_score": avg_risk,
                        "high_risk_loans_count": sd["high_risk_count"],
                        "high_risk_exposure": sd["high_risk_exp"],
                        "average_delinquency_days": avg_del,
                        "average_income": avg_inc,
                    }
                )

                if avg_risk > highest_risk_score:
                    highest_risk_score = avg_risk
                    highest_risk_segment = seg_val
                    highest_risk_type = seg_type

        # 2. Top Adverse Factors & Driver averages
        driver_waterfall = []
        all_driver_scores = {name: [] for name in driver_names}
        for ass_id, d_list in driver_breakdowns_map.items():
            for d in d_list:
                all_driver_scores[d.driver_name].append(d.contribution_score or 0.0)

        for name, scores in all_driver_scores.items():
            avg_contrib = round(calculate_mean(scores), 2) if scores else 0.0
            driver_waterfall.append({"driver": name, "avg_contribution": avg_contrib})
        driver_waterfall = sorted(driver_waterfall, key=lambda x: x["avg_contribution"], reverse=True)

        # 3. Root Cause Summary (identifying drivers in worst segment)
        root_cause_summary = "No significant risk anomalies identified."
        if highest_risk_segment and highest_risk_score > 0:
            sd = segments[highest_risk_type][highest_risk_segment]
            seg_drivers = [
                {"driver": d_name, "avg_contrib": round(calculate_mean(scores), 2)}
                for d_name, scores in sd["driver_contribs"].items()
            ]
            seg_drivers = sorted(seg_drivers, key=lambda x: x["avg_contrib"], reverse=True)[:3]
            drivers_desc = ", ".join([f"{d['driver']} (avg {d['avg_contrib']:.1f})" for d in seg_drivers])
            root_cause_summary = (
                f"Segment '{highest_risk_segment}' ({highest_risk_type}) exhibits elevated credit risk "
                f"with an average score of {highest_risk_score:.2f}. "
                f"Primary root-cause drivers include: {drivers_desc}."
            )

        # 4. Correlation Analysis
        corr_variables = [
            "income",
            "loan_amount",
            "outstanding_amount",
            "delinquency_days",
            "repayment_burden_ratio",
            "risk_score",
        ]
        # Gather columns vectors
        columns_data = {var: [] for var in corr_variables}
        for loan, borrower in records:
            ass = assessments_map.get(loan.id)
            score = ass.risk_score if ass else 0.0

            columns_data["income"].append(borrower.income if borrower and borrower.income is not None else 0.0)
            columns_data["loan_amount"].append(loan.loan_amount if loan.loan_amount is not None else 0.0)
            columns_data["outstanding_amount"].append(
                loan.outstanding_amount if loan.outstanding_amount is not None else 0.0
            )
            columns_data["delinquency_days"].append(float(loan.delinquency_days or 0.0))
            columns_data["repayment_burden_ratio"].append(
                loan.repayment_burden_ratio if loan.repayment_burden_ratio is not None else 0.0
            )
            columns_data["risk_score"].append(score)

        columns_vectors = [columns_data[var] for var in corr_variables]
        corr_matrix = calculate_correlation_matrix(columns_vectors)

        correlation_analysis = {
            "variables": corr_variables,
            "matrix": [[round(val, 4) for val in row] for row in corr_matrix],
        }

        # 5. Anomalies & Hot spots
        anomalies = []
        overall_avg_del = calculate_mean(overall_delinquencies)
        overall_std_del = calculate_std_dev(overall_delinquencies)
        del_threshold = max(30.0, overall_avg_del + 1.5 * overall_std_del)

        for item in segment_comparison_table:
            if item["average_delinquency_days"] > del_threshold:
                anomalies.append(
                    {
                        "segment_value": item["segment_value"],
                        "segment_type": item["segment_type"],
                        "anomaly_type": "Elevated Delinquency Days",
                        "value": item["average_delinquency_days"],
                        "threshold": round(del_threshold, 2),
                    }
                )

        # Hot spots (High exposure + high risk)
        hot_spots = []
        total_exp = sum(l.outstanding_amount or 0.0 for l, b in records)
        for item in segment_comparison_table:
            exp_pct = (item["outstanding_exposure"] / total_exp * 100) if total_exp else 0.0
            if exp_pct > 25.0 and item["average_risk_score"] > 50.0:
                hot_spots.append(
                    {
                        "segment_value": item["segment_value"],
                        "segment_type": item["segment_type"],
                        "exposure_percentage": round(exp_pct, 2),
                        "average_risk_score": item["average_risk_score"],
                    }
                )

        # Bubble Chart Visualization Slices
        bubble_chart = []
        for item in segment_comparison_table:
            bubble_chart.append(
                {
                    "segment_name": f"{item['segment_value']} ({item['segment_type']})",
                    "x_exposure": item["outstanding_exposure"],
                    "y_risk": item["average_risk_score"],
                    "size_loans": item["loans_count"],
                }
            )

        # Drill through borrower/segment table
        drill_through = []
        for loan, borrower in records:
            ass = assessments_map.get(loan.id)
            score = ass.risk_score if ass else 0.0
            cat_str = self._get_cat_str(ass.risk_category) if ass else "LOW"

            drill_through.append(
                {
                    "source_borrower_id": borrower.source_borrower_id if borrower else "N/A",
                    "source_loan_id": loan.source_loan_id or "N/A",
                    "region": borrower.region if borrower else "N/A",
                    "loan_purpose": loan.loan_purpose or "N/A",
                    "loan_amount": loan.loan_amount,
                    "risk_score": score,
                    "risk_category": cat_str,
                }
            )

        return {
            "segment_comparisons": segment_comparison_table,
            "root_cause_summary": root_cause_summary,
            "correlation_analysis": correlation_analysis,
            "top_adverse_factors": driver_waterfall[:5],
            "segment_anomalies": anomalies,
            "portfolio_hot_spots": hot_spots,
            "visualizations": {
                "driver_waterfall": driver_waterfall,
                "correlation_matrix": correlation_analysis,
                "segment_comparison_table": segment_comparison_table,
                "bubble_chart": bubble_chart,
                "drill_through_table": drill_through[:50],  # page size cap
            },
        }

    def _build_empty_response(self, dataset_id: uuid.UUID, version_id: uuid.UUID) -> Dict[str, Any]:
        return {
            "segment_comparisons": [],
            "root_cause_summary": "No data records available.",
            "correlation_analysis": {"variables": [], "matrix": []},
            "top_adverse_factors": [],
            "segment_anomalies": [],
            "portfolio_hot_spots": [],
            "visualizations": {
                "driver_waterfall": [],
                "correlation_matrix": {"variables": [], "matrix": []},
                "segment_comparison_table": [],
                "bubble_chart": [],
                "drill_through_table": [],
            },
        }
