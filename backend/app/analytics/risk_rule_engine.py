import uuid
from typing import Any, Dict, Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums.risk_category import RiskCategoryEnum
from app.models.borrower import Borrower
from app.models.loan import Loan
from app.models.risk_assessment import RiskAssessment
from app.models.risk_driver_breakdown import RiskDriverBreakdown


class RiskRuleEngine:
    """
    Deterministic risk analytics engine utilizing explainable business rules.
    Assesses, scores, and categorizes credit risk for borrowers and loans.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def assess_risk(self, dataset_id: uuid.UUID, version_id: uuid.UUID) -> Dict[str, Any]:
        """
        Runs risk assessments on all loans and borrowers for a specific dataset version.
        Persists results to the database and builds visualization payload shapes.
        """
        # 1. Idempotency: Clear previous risk assessments for this dataset version
        await self.session.execute(
            delete(RiskAssessment).where(
                RiskAssessment.dataset_id == dataset_id, RiskAssessment.version_id == version_id
            )
        )
        await self.session.flush()

        # 2. Query loans and left-joined borrowers
        stmt = (
            select(Loan, Borrower)
            .join(Borrower, Loan.borrower_id == Borrower.id, isouter=True)
            .where(Loan.dataset_id == dataset_id, Loan.version_id == version_id)
        )
        result = await self.session.execute(stmt)
        records = result.all()

        if not records:
            return self._build_empty_response(dataset_id, version_id)

        assessments_list = []
        high_risk_borrowers = []
        high_risk_exposure = []

        # Categorized lists for dashboard calculations
        scores_by_income_group = {
            "Under $30k": [],
            "$30k - $60k": [],
            "$60k - $100k": [],
            "$100k - $150k": [],
            "$150k+": [],
        }
        scores_by_employment = {}
        regions_set = set()
        heatmap_data = {}  # (region, income_group) -> list of scores
        driver_contributions = {
            "Delinquency Days": [],
            "Historical Credit Behavior": [],
            "Repayment Burden (DTI)": [],
            "Income Level": [],
            "Employment Stability": [],
            "Loan Amount": [],
            "Outstanding Amount": [],
            "Loan Term": [],
            "Regional Risk Indicator": [],
            "Loan Purpose": [],
            "Asset Value": [],
        }

        # 3. Assess each record
        for loan, borrower in records:
            result_details = self._assess_single_loan(loan, borrower)
            score = result_details["score"]
            category = result_details["category"]
            summary = result_details["summary"]
            breakdowns = result_details["breakdowns"]

            borrower_id = borrower.id if borrower else None

            # Persist RiskAssessment
            assessment = RiskAssessment(
                id=uuid.uuid4(),
                dataset_id=dataset_id,
                version_id=version_id,
                borrower_id=borrower_id,
                loan_id=loan.id,
                risk_score=score,
                risk_category=category,
                risk_driver_summary=summary,
                assessment_version=1,
                rule_set_version="v1.0.0",
            )
            self.session.add(assessment)

            # Persist RiskDriverBreakdowns
            for b in breakdowns:
                db_breakdown = RiskDriverBreakdown(
                    id=uuid.uuid4(),
                    risk_assessment_id=assessment.id,
                    driver_name=b["driver_name"],
                    driver_value=b["driver_value"],
                    driver_weight=b["driver_weight"],
                    contribution_score=b["contribution_score"],
                    explanation=b["explanation"],
                )
                self.session.add(db_breakdown)
                # Keep track of driver contributions
                if b["driver_name"] in driver_contributions:
                    driver_contributions[b["driver_name"]].append(b["contribution_score"])

            assessments_list.append({"score": score, "category": category})

            # Aggregations for visual charts
            income = borrower.income if borrower else None
            income_group = self._get_income_group(income)
            if income_group in scores_by_income_group:
                scores_by_income_group[income_group].append(score)

            emp_type = borrower.employment_type if borrower else "N/A"
            if emp_type not in scores_by_employment:
                scores_by_employment[emp_type] = []
            scores_by_employment[emp_type].append(score)

            region = borrower.region if borrower else "N/A"
            if region != "N/A":
                regions_set.add(region)
                key = (region, income_group)
                if key not in heatmap_data:
                    heatmap_data[key] = []
                heatmap_data[key].append(score)

            # High risk categorization tables
            if category == RiskCategoryEnum.HIGH:
                if borrower:
                    high_risk_borrowers.append(
                        {
                            "source_borrower_id": borrower.source_borrower_id or "N/A",
                            "age": borrower.age,
                            "gender": borrower.gender,
                            "income": borrower.income,
                            "risk_score": score,
                        }
                    )
                high_risk_exposure.append(
                    {
                        "source_loan_id": loan.source_loan_id or "N/A",
                        "loan_amount": loan.loan_amount,
                        "outstanding_amount": loan.outstanding_amount,
                        "delinquency_days": loan.delinquency_days,
                        "interest_rate": loan.interest_rate,
                        "risk_score": score,
                    }
                )

        await self.session.flush()

        # 4. Compute summaries
        total_records = len(assessments_list)
        avg_score = round(sum(a["score"] for a in assessments_list) / total_records, 2)

        donut_counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
        for a in assessments_list:
            donut_counts[a["category"].value] += 1

        donut_viz = {
            cat: {"count": count, "percentage": round((count / total_records) * 100, 2)}
            for cat, count in donut_counts.items()
        }

        # Average risk category resolve
        if avg_score < 15.0:
            avg_category = RiskCategoryEnum.LOW
        elif avg_score < 25.0:
            avg_category = RiskCategoryEnum.MEDIUM
        else:
            avg_category = RiskCategoryEnum.HIGH

        # Income vs Risk scatter
        income_vs_risk = []
        loan_amt_vs_risk = []
        for loan, borrower in records:
            res_score = self._assess_single_loan(loan, borrower)["score"]
            if borrower and borrower.income is not None:
                income_vs_risk.append({"income": borrower.income, "risk_score": res_score})
            if loan.loan_amount is not None:
                loan_amt_vs_risk.append({"loan_amount": loan.loan_amount, "risk_score": res_score})

        # Donut & segments formatting
        avg_by_income = {
            group: round(sum(slist) / len(slist), 2) if slist else 0.0
            for group, slist in scores_by_income_group.items()
        }
        avg_by_employment = {
            emp: round(sum(slist) / len(slist), 2) if slist else 0.0 for emp, slist in scores_by_employment.items()
        }

        # Driver waterfall chart (average contribution of each driver)
        driver_waterfall = [
            {"driver": driver, "avg_contribution": round(sum(scores) / len(scores), 2) if scores else 0.0}
            for driver, scores in driver_contributions.items()
        ]

        # Heatmap matrix
        heatmap_regions = sorted(list(regions_set))
        heatmap_income_groups = ["Under $30k", "$30k - $60k", "$60k - $100k", "$100k - $150k", "$150k+"]
        heatmap_matrix = []
        for reg in heatmap_regions:
            row_vals = []
            for inc in heatmap_income_groups:
                scores_list = heatmap_data.get((reg, inc), [])
                row_vals.append(round(sum(scores_list) / len(scores_list), 2) if scores_list else 0.0)
            heatmap_matrix.append(row_vals)

        risk_heatmap_viz = {
            "regions": heatmap_regions,
            "income_groups": heatmap_income_groups,
            "matrix": heatmap_matrix,
        }

        # Final Payload
        return {
            "risk_score": avg_score,
            "risk_category": avg_category.value,
            "risk_driver_summary": f"Dataset average risk score is {avg_score:.2f} ({avg_category.value}). Total assessed loans: {total_records}.",
            "driver_contribution_breakdown": driver_waterfall,
            "risk_segmentation": {
                "income_groups": avg_by_income,
                "employment_types": avg_by_employment,
                "regions": {
                    reg: (
                        round(
                            sum([scores_list for (r, inc), scores_list in heatmap_data.items() if r == reg][0])
                            / len([scores_list for (r, inc), scores_list in heatmap_data.items() if r == reg][0]),
                            2,
                        )
                        if [scores_list for (r, inc), scores_list in heatmap_data.items() if r == reg]
                        else 0.0
                    )
                    for reg in heatmap_regions
                },
            },
            "high_risk_borrowers": high_risk_borrowers,
            "high_risk_exposure": high_risk_exposure,
            "visualizations": {
                "risk_distribution_donut": donut_viz,
                "risk_by_income_group": avg_by_income,
                "income_vs_risk_scatter": income_vs_risk,
                "loan_amount_vs_risk_scatter": loan_amt_vs_risk,
                "employment_type_vs_risk_bar": avg_by_employment,
                "risk_driver_waterfall": driver_waterfall,
                "risk_heatmap": risk_heatmap_viz,
                "high_risk_exposure_table": high_risk_exposure,
            },
        }

    def _assess_single_loan(self, loan: Loan, borrower: Optional[Borrower]) -> Dict[str, Any]:
        """Evaluates scoring drivers deterministically for a single loan/borrower context."""
        delinquency_days = loan.delinquency_days
        historical_default = loan.historical_default_flag
        repayment_burden = loan.repayment_burden_ratio
        income = borrower.income if borrower else None
        employment = borrower.employment_type if borrower else None
        loan_amount = loan.loan_amount
        outstanding = loan.outstanding_amount
        loan_term = loan.loan_term
        region = borrower.region if borrower else None
        loan_purpose = loan.loan_purpose
        asset_value = loan.asset_value

        breakdowns = []
        total_score = 0.0

        # 1. Delinquency Days (Max 20.0)
        del_score = 0.0
        del_explain = "No Delinquency"
        if delinquency_days is not None:
            if delinquency_days > 90:
                del_score = 20.0
                del_explain = f"Critical delinquency over 90 days ({delinquency_days} DPD)"
            elif delinquency_days > 30:
                del_score = 12.0
                del_explain = f"Warning delinquency over 30 days ({delinquency_days} DPD)"
            elif delinquency_days > 0:
                del_score = 5.0
                del_explain = f"Caution delinquency up to 30 days ({delinquency_days} DPD)"
            else:
                del_explain = "Delinquency days is 0 (Current)"
        breakdowns.append(
            {
                "driver_name": "Delinquency Days",
                "driver_value": str(delinquency_days) if delinquency_days is not None else "N/A",
                "driver_weight": 0.20,
                "contribution_score": del_score,
                "explanation": del_explain,
            }
        )
        total_score += del_score

        # 2. Historical Credit Behavior (Max 15.0)
        hist_score = 0.0
        hist_explain = "No historical defaults detected"
        if historical_default is True:
            hist_score = 15.0
            hist_explain = "Critical: Historical credit default flag detected"
        elif historical_default is False:
            hist_explain = "No historical default record"
        breakdowns.append(
            {
                "driver_name": "Historical Credit Behavior",
                "driver_value": str(historical_default) if historical_default is not None else "N/A",
                "driver_weight": 0.15,
                "contribution_score": hist_score,
                "explanation": hist_explain,
            }
        )
        total_score += hist_score

        # 3. Repayment Burden (DTI) (Max 15.0)
        burden_score = 0.0
        burden_explain = "Low repayment burden"
        if repayment_burden is not None:
            if repayment_burden > 0.50:
                burden_score = 15.0
                burden_explain = f"Critical repayment burden DTI over 50% ({repayment_burden:.1%})"
            elif repayment_burden > 0.35:
                burden_score = 10.0
                burden_explain = f"Elevated repayment burden DTI between 35% and 50% ({repayment_burden:.1%})"
            else:
                burden_explain = f"Low repayment burden DTI ratio ({repayment_burden:.1%})"
        breakdowns.append(
            {
                "driver_name": "Repayment Burden (DTI)",
                "driver_value": f"{repayment_burden:.4f}" if repayment_burden is not None else "N/A",
                "driver_weight": 0.15,
                "contribution_score": burden_score,
                "explanation": burden_explain,
            }
        )
        total_score += burden_score

        # 4. Income Level (Max 10.0)
        income_score = 0.0
        income_explain = "Sufficient annual income"
        if income is not None:
            if income < 30000:
                income_score = 10.0
                income_explain = f"Low annual income under $30,000 (${income:,.2f})"
            elif income < 60000:
                income_score = 5.0
                income_explain = f"Moderate annual income between $30k and $60k (${income:,.2f})"
            else:
                income_explain = f"Sufficient annual income (${income:,.2f})"
        breakdowns.append(
            {
                "driver_name": "Income Level",
                "driver_value": f"{income:.2f}" if income is not None else "N/A",
                "driver_weight": 0.10,
                "contribution_score": income_score,
                "explanation": income_explain,
            }
        )
        total_score += income_score

        # 5. Employment Stability (Max 10.0)
        emp_score = 0.0
        emp_explain = "Stable employment structure"
        if employment is not None:
            emp_lower = employment.lower()
            if "unemployed" in emp_lower or "retired" in emp_lower:
                emp_score = 10.0
                emp_explain = f"Critical: No active employment income ({employment})"
            elif "self" in emp_lower or "freelance" in emp_lower or "contractor" in emp_lower:
                emp_score = 5.0
                emp_explain = f"Caution: Higher volatility in employment income ({employment})"
        breakdowns.append(
            {
                "driver_name": "Employment Stability",
                "driver_value": employment if employment is not None else "N/A",
                "driver_weight": 0.10,
                "contribution_score": emp_score,
                "explanation": emp_explain,
            }
        )
        total_score += emp_score

        # 6. Loan Amount (Max 10.0)
        amt_score = 0.0
        amt_explain = "Low principal exposure"
        if loan_amount is not None:
            if loan_amount > 100000:
                amt_score = 10.0
                amt_explain = f"High: Large loan exposure over $100k (${loan_amount:,.2f})"
            elif loan_amount > 50000:
                amt_score = 5.0
                amt_explain = f"Moderate: Moderate loan exposure between $50k and $100k (${loan_amount:,.2f})"
            else:
                amt_explain = f"Low principal exposure (${loan_amount:,.2f})"
        breakdowns.append(
            {
                "driver_name": "Loan Amount",
                "driver_value": f"{loan_amount:.2f}" if loan_amount is not None else "N/A",
                "driver_weight": 0.10,
                "contribution_score": amt_score,
                "explanation": amt_explain,
            }
        )
        total_score += amt_score

        # 7. Outstanding Amount (Max 5.0)
        out_score = 0.0
        out_explain = "Normal outstanding balance ratio"
        if outstanding is not None and loan_amount and loan_amount > 0:
            ratio = outstanding / loan_amount
            if ratio > 0.90:
                out_score = 5.0
                out_explain = f"High outstanding exposure over 90% of principal ({ratio:.1%})"
            else:
                out_explain = f"Outstanding balance is {ratio:.1%} of principal"
        breakdowns.append(
            {
                "driver_name": "Outstanding Amount",
                "driver_value": f"{outstanding:.2f}" if outstanding is not None else "N/A",
                "driver_weight": 0.05,
                "contribution_score": out_score,
                "explanation": out_explain,
            }
        )
        total_score += out_score

        # 8. Loan Term (Max 5.0)
        term_score = 0.0
        term_explain = "Short-to-medium-term maturity"
        if loan_term is not None:
            if loan_term > 60:
                term_score = 5.0
                term_explain = f"Long-term maturity over 60 months ({loan_term} months)"
            else:
                term_explain = f"Short-to-medium-term maturity ({loan_term} months)"
        breakdowns.append(
            {
                "driver_name": "Loan Term",
                "driver_value": str(loan_term) if loan_term is not None else "N/A",
                "driver_weight": 0.05,
                "contribution_score": term_score,
                "explanation": term_explain,
            }
        )
        total_score += term_score

        # 9. Regional Risk Indicator (Max 5.0)
        reg_score = 0.0
        reg_explain = "Standard regional risk factor"
        if region is not None:
            reg_lower = region.lower()
            if "high-risk" in reg_lower or "east" in reg_lower or "south-east" in reg_lower:
                reg_score = 5.0
                reg_explain = f"Elevated default correlation region ({region})"
        breakdowns.append(
            {
                "driver_name": "Regional Risk Indicator",
                "driver_value": region if region is not None else "N/A",
                "driver_weight": 0.05,
                "contribution_score": reg_score,
                "explanation": reg_explain,
            }
        )
        total_score += reg_score

        # 10. Loan Purpose (Max 3.0)
        purp_score = 0.0
        purp_explain = "Standard loan purpose risk"
        if loan_purpose is not None:
            purp_lower = loan_purpose.lower()
            if "consolidation" in purp_lower or "speculative" in purp_lower or "other" in purp_lower:
                purp_score = 3.0
                purp_explain = f"Higher risk loan purpose category ({loan_purpose})"
        breakdowns.append(
            {
                "driver_name": "Loan Purpose",
                "driver_value": loan_purpose if loan_purpose is not None else "N/A",
                "driver_weight": 0.03,
                "contribution_score": purp_score,
                "explanation": purp_explain,
            }
        )
        total_score += purp_score

        # 11. Asset Value (Max 2.0)
        ltv_score = 0.0
        ltv_explain = "Sound collateral coverage"
        if asset_value is not None and loan_amount is not None and asset_value > 0:
            ltv = loan_amount / asset_value
            if ltv > 1.0:
                ltv_score = 2.0
                ltv_explain = f"Uncollateralized LTV ratio over 100% ({ltv:.1%})"
            else:
                ltv_explain = f"Sound collateral coverage ratio with LTV {ltv:.1%}"
        breakdowns.append(
            {
                "driver_name": "Asset Value",
                "driver_value": f"{asset_value:.2f}" if asset_value is not None else "N/A",
                "driver_weight": 0.02,
                "contribution_score": ltv_score,
                "explanation": ltv_explain,
            }
        )
        total_score += ltv_score

        total_score = min(max(total_score, 0.0), 100.0)

        if total_score < 15.0:
            category = RiskCategoryEnum.LOW
        elif total_score < 25.0:
            category = RiskCategoryEnum.MEDIUM
        else:
            category = RiskCategoryEnum.HIGH

        # Format summary string
        active_drivers = [b for b in breakdowns if b["contribution_score"] > 0.0]
        active_drivers.sort(key=lambda x: x["contribution_score"], reverse=True)
        if active_drivers:
            summary_str = (
                f"Risk rating is {category.value} with a score of {total_score:.1f}/100.0. "
                f"Primary risk drivers: "
                + ", ".join([f"{d['driver_name']} ({d['explanation']})" for d in active_drivers[:3]])
            )
        else:
            summary_str = (
                f"Risk rating is {category.value} with a score of {total_score:.1f}/100.0. No elevated risk factors."
            )

        return {"score": total_score, "category": category, "summary": summary_str, "breakdowns": breakdowns}

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
        """Returns structure for versions containing no valid database records."""
        return {
            "risk_score": 0.0,
            "risk_category": "LOW",
            "risk_driver_summary": "No data records available for analysis.",
            "driver_contribution_breakdown": [],
            "risk_segmentation": {"income_groups": {}, "employment_types": {}, "regions": {}},
            "high_risk_borrowers": [],
            "high_risk_exposure": [],
            "visualizations": {
                "risk_distribution_donut": {},
                "risk_by_income_group": {},
                "income_vs_risk_scatter": [],
                "loan_amount_vs_risk_scatter": [],
                "employment_type_vs_risk_bar": {},
                "risk_driver_waterfall": [],
                "risk_heatmap": {"regions": [], "income_groups": [], "matrix": []},
                "high_risk_exposure_table": [],
            },
        }
