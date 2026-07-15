import logging
import uuid
from typing import Any, Dict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.borrower import Borrower
from app.models.loan import Loan
from app.models.schema_mapping import SchemaMapping
from app.utils.statistics import (
    calculate_iqr_bounds,
    calculate_mean,
    calculate_median,
    calculate_std_dev,
)

logger = logging.getLogger(__name__)


class LoanAnalyticsEngine:
    """
    Deterministic Loan Analytics Engine.
    Computes loan amount distributions, delinquency aging profiles, exposure waterfalls,
    and interest rate distributions without ML/DL.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_metrics(self, dataset_id: uuid.UUID, version_id: uuid.UUID) -> Dict[str, Any]:
        """
        Calculates loan analytics metrics and visualization structures.
        """
        logger.info("Computing Loan Analytics metrics for dataset_id=%s, version_id=%s", dataset_id, version_id)

        # Initialize ExposureCalculationService
        from app.services.analytics.exposure_calculation_service import ExposureCalculationService
        exposure_service = ExposureCalculationService(self.db)

        # 1. Fetch Schema Mappings
        mappings_stmt = select(SchemaMapping).where(
            SchemaMapping.dataset_id == dataset_id, SchemaMapping.version_id == version_id
        )
        mappings_res = await self.db.execute(mappings_stmt)
        mappings = list(mappings_res.scalars().all())
        mapped_fields = {m.canonical_field for m in mappings}

        def is_mapped(f: str) -> bool:
            return f in mapped_fields

        # 2. Fetch Loans & Borrowers
        loan_stmt = select(Loan).where(Loan.dataset_id == dataset_id, Loan.version_id == version_id)
        loan_res = await self.db.execute(loan_stmt)
        loans = list(loan_res.scalars().all())

        borrower_stmt = select(Borrower).where(Borrower.dataset_id == dataset_id, Borrower.version_id == version_id)
        borrower_res = await self.db.execute(borrower_stmt)
        borrowers = list(borrower_res.scalars().all())
        borrower_by_id = {b.id: b for b in borrowers}

        if not loans:
            return {
                "total_loans": 0,
                "loan_amount_distribution": "unavailable: no records found",
                "outstanding_exposure": "unavailable: no records found",
                "average_loan_amount": "unavailable: no records found",
                "median_loan_amount": "unavailable: no records found",
                "loan_purpose_distribution": "unavailable: no records found",
                "interest_rate_distribution": "unavailable: no records found",
                "loan_term_distribution": "unavailable: no records found",
                "annuity_distribution": "unavailable: no records found",
                "repayment_burden_ratio": "unavailable: no records found",
                "delinquency_buckets": "unavailable: no records found",
                "loan_status_distribution": "unavailable: no records found",
                "exposure_by_loan_purpose": "unavailable: no records found",
                "exposure_by_loan_status": "unavailable: no records found",
                "visualizations": {
                    "loan_exposure_bars": {},
                    "loan_purpose_treemap": {},
                    "delinquency_aging_table": [],
                    "loan_amount_histogram": {},
                    "interest_rate_boxplot": {},
                    "exposure_waterfall": [],
                },
            }

        # 3. Basic Loan Computations
        total_loans = len(loans)

        # Loan amount distribution
        if not is_mapped("loan_amount"):
            loan_amount_distribution = "unavailable: loan_amount canonical field is not mapped"
            average_loan_amount = "unavailable: loan_amount canonical field is not mapped"
            median_loan_amount = "unavailable: loan_amount canonical field is not mapped"
        else:
            amt_vals = [l.loan_amount for l in loans if l.loan_amount is not None]
            if not amt_vals:
                loan_amount_distribution = "unavailable: no loan_amount values found"
                average_loan_amount = "unavailable: no loan_amount values found"
                median_loan_amount = "unavailable: no loan_amount values found"
            else:
                mean_amt = calculate_mean(amt_vals)
                med_amt = calculate_median(amt_vals)
                std_amt = calculate_std_dev(amt_vals, mean_amt)
                loan_amount_distribution = {
                    "min": min(amt_vals),
                    "max": max(amt_vals),
                    "mean": round(mean_amt, 2),
                    "median": round(med_amt, 2),
                    "std_dev": round(std_amt, 2),
                }
                average_loan_amount = round(mean_amt, 2)
                median_loan_amount = round(med_amt, 2)

        # Outstanding exposure
        if not is_mapped("outstanding_amount") and not is_mapped("loan_amount"):
            outstanding_exposure = "unavailable: outstanding_amount and loan_amount canonical fields are not mapped"
        else:
            out_vals = [l.outstanding_amount if l.outstanding_amount is not None else l.loan_amount for l in loans]
            outstanding_exposure = round(sum(v for v in out_vals if v is not None), 2)

        # Loan purpose distribution
        if not is_mapped("loan_purpose"):
            loan_purpose_distribution = "unavailable: loan_purpose canonical field is not mapped"
        else:
            dist = {}
            for l in loans:
                purp = l.loan_purpose or "Unknown"
                dist[purp] = dist.get(purp, 0) + 1
            loan_purpose_distribution = dist

        # Interest rate distribution
        if not is_mapped("interest_rate"):
            interest_rate_distribution = "unavailable: interest_rate canonical field is not mapped"
        else:
            rate_vals = [l.interest_rate for l in loans if l.interest_rate is not None]
            if rate_vals and all(r is not None and r <= 1.0 for r in rate_vals):
                rate_vals = [r * 100.0 for r in rate_vals]
            if not rate_vals:
                interest_rate_distribution = "unavailable: no interest_rate values found"
            else:
                mean_rate = calculate_mean(rate_vals)
                median_rate = calculate_median(rate_vals)
                std_rate = calculate_std_dev(rate_vals, mean_rate)
                interest_rate_distribution = {
                    "min": min(rate_vals),
                    "max": max(rate_vals),
                    "mean": round(mean_rate, 4),
                    "median": round(median_rate, 4),
                    "std_dev": round(std_rate, 4),
                }

        # Loan term distribution
        if not is_mapped("loan_term"):
            loan_term_distribution = "unavailable: loan_term canonical field is not mapped"
        else:
            term_vals = [l.loan_term for l in loans if l.loan_term is not None]
            if not term_vals:
                loan_term_distribution = "unavailable: no loan_term values found"
            else:
                term_vals_float = [float(x) for x in term_vals]
                mean_term = calculate_mean(term_vals_float)
                median_term = calculate_median(term_vals_float)
                t_counts = {}
                for t in term_vals:
                    t_counts[t] = t_counts.get(t, 0) + 1
                loan_term_distribution = {
                    "mean": round(mean_term, 2),
                    "median": round(median_term, 2),
                    "counts": t_counts,
                }

        # Annuity distribution
        if not is_mapped("annuity_amount"):
            annuity_distribution = "unavailable: annuity_amount canonical field is not mapped"
        else:
            ann_vals = [l.annuity_amount for l in loans if l.annuity_amount is not None]
            if not ann_vals:
                annuity_distribution = "unavailable: no annuity_amount values found"
            else:
                mean_ann = calculate_mean(ann_vals)
                median_ann = calculate_median(ann_vals)
                std_ann = calculate_std_dev(ann_vals, mean_ann)
                annuity_distribution = {
                    "min": min(ann_vals),
                    "max": max(ann_vals),
                    "mean": round(mean_ann, 2),
                    "median": round(median_ann, 2),
                    "std_dev": round(std_ann, 2),
                }

        # Repayment burden ratio (credit burden)
        repayment_burden_vals = []
        for l in loans:
            ratio = l.repayment_burden_ratio
            if ratio is None and l.annuity_amount is not None:
                b = borrower_by_id.get(l.borrower_id) if l.borrower_id else None
                if b and b.income and b.income > 0:
                    annual_ratio = l.annuity_amount / b.income
                    monthly_ratio = (l.annuity_amount * 12.0) / b.income
                    if monthly_ratio <= 1.0:
                        ratio = monthly_ratio
                    else:
                        ratio = annual_ratio
            if ratio is not None:
                repayment_burden_vals.append(ratio)

        if not repayment_burden_vals:
            repayment_burden_ratio = None
        else:
            mean_ratio = calculate_mean(repayment_burden_vals)
            repayment_burden_ratio = round(mean_ratio, 4)

        # Delinquency buckets
        if not is_mapped("delinquency_days") and not is_mapped("historical_default_flag") and not is_mapped("loan_status"):
            delinquency_buckets = "unavailable: delinquency fields are not mapped"
        else:
            buckets = {
                "Current": {"count": 0, "exposure": 0.0},
                "1-30 DPD": {"count": 0, "exposure": 0.0},
                "31-60 DPD": {"count": 0, "exposure": 0.0},
                "61-90 DPD": {"count": 0, "exposure": 0.0},
                "90+ DPD": {"count": 0, "exposure": 0.0},
            }
            for l in loans:
                dpd = l.delinquency_days
                if dpd is None:
                    if l.historical_default_flag is True:
                        dpd = 91
                    elif l.loan_status in ("Default", "Charged Off", "Charged-Off"):
                        dpd = 91
                    elif l.loan_status in ("Delinquent",):
                        dpd = 45
                    else:
                        dpd = 0

                exp = l.outstanding_amount if l.outstanding_amount is not None else l.loan_amount
                if exp is None:
                    exp = 0.0

                if dpd <= 0:
                    buckets["Current"]["count"] += 1
                    buckets["Current"]["exposure"] += exp
                elif dpd <= 30:
                    buckets["1-30 DPD"]["count"] += 1
                    buckets["1-30 DPD"]["exposure"] += exp
                elif dpd <= 60:
                    buckets["31-60 DPD"]["count"] += 1
                    buckets["31-60 DPD"]["exposure"] += exp
                elif dpd <= 90:
                    buckets["61-90 DPD"]["count"] += 1
                    buckets["61-90 DPD"]["exposure"] += exp
                else:
                    buckets["90+ DPD"]["count"] += 1
                    buckets["90+ DPD"]["exposure"] += exp

            for b_name in buckets:
                buckets[b_name]["exposure"] = round(buckets[b_name]["exposure"], 2)
            delinquency_buckets = buckets

        # Loan status distribution
        if not is_mapped("loan_status"):
            loan_status_distribution = "unavailable: loan_status canonical field is not mapped"
        else:
            dist = {}
            for l in loans:
                st = l.loan_status or "Unknown"
                dist[st] = dist.get(st, 0) + 1
            loan_status_distribution = dist

        # Exposure by purpose using centralized ExposureCalculationService
        exposure_by_loan_purpose = await exposure_service.calculate_exposure_by_dimension(dataset_id, "loan_purpose")

        # Exposure by status using centralized ExposureCalculationService
        exposure_by_loan_status = await exposure_service.calculate_exposure_by_dimension(dataset_id, "loan_status")

        # 4. Visualizations
        loan_exposure_bars = exposure_by_loan_status

        # Treemap
        loan_purpose_treemap = {}
        if isinstance(loan_purpose_distribution, dict):
            loan_purpose_treemap = {
                "name": "Total Loans",
                "children": [
                    {
                        "name": purp,
                        "count": count,
                        "exposure": (
                            exposure_by_loan_purpose.get(purp, 0.0)
                            if isinstance(exposure_by_loan_purpose, dict)
                            else 0.0
                        ),
                    }
                    for purp, count in loan_purpose_distribution.items()
                ],
            }

        # Delinquency aging table
        delinquency_aging_table = []
        if isinstance(delinquency_buckets, dict):
            for b_name, b_val in delinquency_buckets.items():
                delinquency_aging_table.append(
                    {
                        "bucket": b_name,
                        "count": b_val["count"],
                        "exposure": b_val["exposure"],
                        "percentage_of_loans": (
                            round((b_val["count"] / total_loans) * 100.0, 2) if total_loans > 0 else 0.0
                        ),
                    }
                )

        # Histogram
        loan_amount_histogram = {}
        if is_mapped("loan_amount"):
            amt_vals = [l.loan_amount for l in loans if l.loan_amount is not None]
            if amt_vals:
                import numpy as np

                try:
                    counts, bin_edges = np.histogram(amt_vals, bins=10)
                    loan_amount_histogram = {
                        "counts": counts.tolist(),
                        "bins": [
                            f"{round(float(bin_edges[idx]), 2)} - {round(float(bin_edges[idx+1]), 2)}"
                            for idx in range(len(counts))
                        ],
                    }
                except Exception as e:
                    logger.warning("Failed to generate loan amount histogram: %s", e)

        # Interest rate boxplot
        interest_rate_boxplot = {}
        if is_mapped("interest_rate"):
            rate_vals = [l.interest_rate for l in loans if l.interest_rate is not None]
            if rate_vals and all(r is not None and r <= 1.0 for r in rate_vals):
                rate_vals = [r * 100.0 for r in rate_vals]
            if rate_vals:
                med_rate = calculate_median(rate_vals)
                q1, q3, low, up = calculate_iqr_bounds(rate_vals)
                normal_rates = [x for x in rate_vals if low <= x <= up]
                interest_rate_boxplot = {
                    "min": min(normal_rates) if normal_rates else min(rate_vals),
                    "q1": q1,
                    "median": med_rate,
                    "q3": q3,
                    "max": max(normal_rates) if normal_rates else max(rate_vals),
                }

        # Exposure waterfall
        exposure_waterfall = []
        if is_mapped("loan_amount"):
            total_loan_amt = sum(l.loan_amount for l in loans if l.loan_amount is not None)
            total_outstanding_amt = (
                sum(l.outstanding_amount for l in loans if l.outstanding_amount is not None)
                if is_mapped("outstanding_amount")
                else total_loan_amt
            )
            total_repaid_amt = max(0.0, total_loan_amt - total_outstanding_amt)

            total_defaulted_amt = 0.0
            for l in loans:
                is_default = False
                if l.historical_default_flag is True:
                    is_default = True
                elif l.delinquency_days is not None and l.delinquency_days > 90:
                    is_default = True
                elif l.loan_status in ("Default", "Charged Off", "Charged-Off"):
                    is_default = True

                if is_default:
                    exp = l.outstanding_amount if l.outstanding_amount is not None else l.loan_amount
                    if exp is not None:
                        total_defaulted_amt += exp

            exposure_waterfall = [
                {"label": "Total Originated", "value": round(total_loan_amt, 2), "type": "total"},
                {"label": "Repaid Amount", "value": round(-total_repaid_amt, 2), "type": "subtraction"},
                {"label": "Active Outstanding", "value": round(total_outstanding_amt, 2), "type": "remaining"},
                {"label": "Defaulted / Non-Performing", "value": round(total_defaulted_amt, 2), "type": "info"},
            ]

        return {
            "total_loans": total_loans,
            "loan_amount_distribution": loan_amount_distribution,
            "outstanding_exposure": outstanding_exposure,
            "average_loan_amount": average_loan_amount,
            "median_loan_amount": median_loan_amount,
            "loan_purpose_distribution": loan_purpose_distribution,
            "interest_rate_distribution": interest_rate_distribution,
            "loan_term_distribution": loan_term_distribution,
            "annuity_distribution": annuity_distribution,
            "repayment_burden_ratio": repayment_burden_ratio,
            "delinquency_buckets": delinquency_buckets,
            "loan_status_distribution": loan_status_distribution,
            "exposure_by_loan_purpose": exposure_by_loan_purpose,
            "exposure_by_loan_status": exposure_by_loan_status,
            "visualizations": {
                "loan_exposure_bars": loan_exposure_bars,
                "loan_purpose_treemap": loan_purpose_treemap,
                "delinquency_aging_table": delinquency_aging_table,
                "loan_amount_histogram": loan_amount_histogram,
                "interest_rate_boxplot": interest_rate_boxplot,
                "exposure_waterfall": exposure_waterfall,
            },
        }
