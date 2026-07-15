import logging
import uuid
from typing import Any, Dict, Optional

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


class BorrowerAnalyticsEngine:
    """
    Deterministic Borrower Analytics Engine.
    Computes demographics, income bands, employment distributions, segment risk,
    and exposure configurations without any ML/DL constructs.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_metrics(self, dataset_id: uuid.UUID, version_id: uuid.UUID) -> Dict[str, Any]:
        """
        Calculates borrower demographics distribution, income bands, and risk segments.
        """
        logger.info("Computing Borrower Analytics metrics for dataset_id=%s, version_id=%s", dataset_id, version_id)

        # 1. Fetch Schema Mappings
        mappings_stmt = select(SchemaMapping).where(
            SchemaMapping.dataset_id == dataset_id, SchemaMapping.version_id == version_id
        )
        mappings_res = await self.db.execute(mappings_stmt)
        mappings = list(mappings_res.scalars().all())
        mapped_fields = {m.canonical_field for m in mappings}

        def is_mapped(f: str) -> bool:
            return f in mapped_fields

        # 2. Fetch Borrowers & Loans
        borrower_stmt = select(Borrower).where(Borrower.dataset_id == dataset_id, Borrower.version_id == version_id)
        borrower_res = await self.db.execute(borrower_stmt)
        borrowers = list(borrower_res.scalars().all())

        loan_stmt = select(Loan).where(Loan.dataset_id == dataset_id, Loan.version_id == version_id)
        loan_res = await self.db.execute(loan_stmt)
        loans = list(loan_res.scalars().all())

        if not borrowers:
            return {
                "borrower_count": 0,
                "income_distribution": "unavailable: no records found",
                "income_bands": "unavailable: no records found",
                "employment_distribution": "unavailable: no records found",
                "age_bands": "unavailable: no records found",
                "occupation_distribution": "unavailable: no records found",
                "education_distribution": "unavailable: no records found",
                "marital_status_distribution": "unavailable: no records found",
                "region_distribution": "unavailable: no records found",
                "family_size_distribution": "unavailable: no records found",
                "risk_by_borrower_segment": "unavailable: no records found",
                "exposure_by_borrower_segment": "unavailable: no records found",
                "visualizations": {
                    "bar_charts": {},
                    "stacked_bars": {},
                    "histograms": {},
                    "boxplots": {},
                    "heatmaps": {},
                    "segment_comparison_matrix": [],
                },
            }

        # Link loans to borrowers
        borrower_loans = {}
        for l in loans:
            if l.borrower_id:
                if l.borrower_id not in borrower_loans:
                    borrower_loans[l.borrower_id] = []
                borrower_loans[l.borrower_id].append(l)

        # 3. Compute Basic Metrics & Distributions
        borrower_count = (
            len(borrowers) if is_mapped("borrower_id") else "unavailable: borrower_id canonical field is not mapped"
        )

        # Income stats
        if not is_mapped("income"):
            income_distribution = "unavailable: income canonical field is not mapped"
            income_bands = "unavailable: income canonical field is not mapped"
        else:
            inc_vals = [b.income for b in borrowers if b.income is not None]
            if not inc_vals:
                income_distribution = "unavailable: no income values found"
                income_bands = "unavailable: no income values found"
            else:
                mean_inc = calculate_mean(inc_vals)
                median_inc = calculate_median(inc_vals)
                std_inc = calculate_std_dev(inc_vals, mean_inc)
                income_distribution = {
                    "min": min(inc_vals),
                    "max": max(inc_vals),
                    "mean": round(mean_inc, 2),
                    "median": round(median_inc, 2),
                    "std_dev": round(std_inc, 2),
                }

                bands = {"Under $30k": 0, "$30k - $60k": 0, "$60k - $100k": 0, "$100k - $150k": 0, "$150k+": 0}
                for inc in inc_vals:
                    if inc < 30000:
                        bands["Under $30k"] += 1
                    elif inc < 60000:
                        bands["$30k - $60k"] += 1
                    elif inc < 100000:
                        bands["$60k - $100k"] += 1
                    elif inc < 150000:
                        bands["$100k - $150k"] += 1
                    else:
                        bands["$150k+"] += 1
                income_bands = bands

        # Categorical distributions helper
        def get_categorical_dist(field_name: str, attr: str) -> Any:
            if not is_mapped(field_name):
                return f"unavailable: {field_name} canonical field is not mapped"
            dist = {}
            for b in borrowers:
                val = getattr(b, attr, None)
                key = str(val).strip() if val is not None else "Unknown"
                dist[key] = dist.get(key, 0) + 1
            return dist

        employment_distribution = get_categorical_dist("employment_type", "employment_type")
        occupation_distribution = get_categorical_dist("occupation", "occupation")
        education_distribution = get_categorical_dist("education_level", "education_level")
        marital_status_distribution = get_categorical_dist("marital_status", "marital_status")
        region_distribution = get_categorical_dist("region", "region")
        family_size_distribution = get_categorical_dist("family_size", "family_size")

        # Age Bands
        if not is_mapped("age"):
            age_bands = "unavailable: age canonical field is not mapped"
        else:
            age_vals = [b.age for b in borrowers if b.age is not None]
            if not age_vals:
                age_bands = "unavailable: no age values found"
            else:
                a_bands = {"Under 25": 0, "25-34": 0, "35-44": 0, "45-54": 0, "55-64": 0, "65+": 0}
                for age in age_vals:
                    if age < 25:
                        a_bands["Under 25"] += 1
                    elif age < 35:
                        a_bands["25-34"] += 1
                    elif age < 45:
                        a_bands["35-44"] += 1
                    elif age < 55:
                        a_bands["45-54"] += 1
                    elif age < 65:
                        a_bands["55-64"] += 1
                    else:
                        a_bands["65+"] += 1
                age_bands = a_bands

        # 4. Segment Risk & Exposure calculations
        def get_age_band_label(age: Optional[int]) -> str:
            if age is None:
                return "Unknown"
            if age < 25:
                return "Under 25"
            if age < 35:
                return "25-34"
            if age < 45:
                return "35-44"
            if age < 55:
                return "45-54"
            if age < 65:
                return "55-64"
            return "65+"

        def get_income_band_label(income: Optional[float]) -> str:
            if income is None:
                return "Unknown"
            if income < 30000:
                return "Under $30k"
            if income < 60000:
                return "$30k - $60k"
            if income < 100000:
                return "$60k - $100k"
            if income < 150000:
                return "$100k - $150k"
            return "$150k+"

        segment_keys = ["employment_type", "age_band", "income_band", "region"]
        borrower_segment_stats = {key: {} for key in segment_keys}

        for b in borrowers:
            b_loans = borrower_loans.get(b.id, [])

            # Retrieve segment keys
            b_segs = {
                "employment_type": b.employment_type or "Unknown" if is_mapped("employment_type") else None,
                "age_band": get_age_band_label(b.age) if is_mapped("age") else None,
                "income_band": get_income_band_label(b.income) if is_mapped("income") else None,
                "region": b.region or "Unknown" if is_mapped("region") else None,
            }

            for seg_type, seg_key in b_segs.items():
                if seg_key is None:
                    continue
                if seg_key not in borrower_segment_stats[seg_type]:
                    borrower_segment_stats[seg_type][seg_key] = {
                        "count": 0,
                        "loans_count": 0,
                        "exposure": 0.0,
                        "default_count": 0,
                        "has_default_flag": is_mapped("historical_default_flag"),
                        "has_delinquency": is_mapped("delinquency_days"),
                        "has_exposure": is_mapped("outstanding_amount") or is_mapped("loan_amount"),
                    }

                stats = borrower_segment_stats[seg_type][seg_key]
                stats["count"] += 1
                for l in b_loans:
                    stats["loans_count"] += 1
                    exp = l.outstanding_amount if l.outstanding_amount is not None else l.loan_amount
                    if exp is not None:
                        stats["exposure"] += exp

                    is_default = False
                    if l.historical_default_flag is True:
                        is_default = True
                    elif l.delinquency_days is not None and l.delinquency_days > 90:
                        is_default = True
                    if is_default:
                        stats["default_count"] += 1

        # Format segment results
        risk_by_borrower_segment = {}
        exposure_by_borrower_segment = {}

        for seg_type in segment_keys:
            mapped_check = seg_type
            if seg_type == "age_band":
                mapped_check = "age"
            elif seg_type == "income_band":
                mapped_check = "income"

            if not is_mapped(mapped_check):
                risk_by_borrower_segment[seg_type] = f"unavailable: {mapped_check} canonical field is not mapped"
                exposure_by_borrower_segment[seg_type] = f"unavailable: {mapped_check} canonical field is not mapped"
                continue

            risk_by_borrower_segment[seg_type] = {}
            exposure_by_borrower_segment[seg_type] = {}

            for key, val in borrower_segment_stats[seg_type].items():
                if not val["has_default_flag"] and not val["has_delinquency"]:
                    risk_by_borrower_segment[seg_type][
                        key
                    ] = "unavailable: risk indicators (default/delinquency) are not mapped"
                else:
                    d_rate = (val["default_count"] / val["loans_count"]) * 100.0 if val["loans_count"] > 0 else 0.0
                    risk_by_borrower_segment[seg_type][key] = {
                        "default_rate": round(d_rate, 2),
                        "default_count": val["default_count"],
                        "total_loans": val["loans_count"],
                    }

                if not val["has_exposure"]:
                    exposure_by_borrower_segment[seg_type][
                        key
                    ] = "unavailable: exposure fields (outstanding/loan amount) are not mapped"
                else:
                    exposure_by_borrower_segment[seg_type][key] = round(val["exposure"], 2)

        # 5. Visualizations Data Shapes
        bar_charts = {}
        if is_mapped("employment_type"):
            bar_charts["employment_type"] = employment_distribution
        if is_mapped("education_level"):
            bar_charts["education_level"] = education_distribution
        if is_mapped("marital_status"):
            bar_charts["marital_status"] = marital_status_distribution

        # Stacked bar: Performing vs Defaulted loans by employment type
        stacked_bars = {}
        if is_mapped("employment_type") and (is_mapped("historical_default_flag") or is_mapped("delinquency_days")):
            categories = list(borrower_segment_stats["employment_type"].keys())
            performing_loans = []
            defaulted_loans = []
            for k in categories:
                v = borrower_segment_stats["employment_type"][k]
                defaulted_loans.append(v["default_count"])
                performing_loans.append(max(0, v["loans_count"] - v["default_count"]))
            stacked_bars["default_status_by_employment"] = {
                "categories": categories,
                "series": {"Performing": performing_loans, "Defaulted": defaulted_loans},
            }

        histograms = {}
        if is_mapped("income"):
            histograms["income"] = {"values": [b.income for b in borrowers if b.income is not None]}
        if is_mapped("age"):
            histograms["age"] = {"values": [b.age for b in borrowers if b.age is not None]}

        # Boxplots: income by employment type, age by marital status
        boxplots = {}
        if is_mapped("income") and is_mapped("employment_type"):
            income_by_emp = {}
            for b in borrowers:
                if b.income is not None:
                    emp = b.employment_type or "Unknown"
                    if emp not in income_by_emp:
                        income_by_emp[emp] = []
                    income_by_emp[emp].append(b.income)

            box_data = []
            for emp, vals in income_by_emp.items():
                if len(vals) >= 2:
                    med = calculate_median(vals)
                    q1, q3, low, up = calculate_iqr_bounds(vals)
                    box_data.append(
                        {
                            "group": emp,
                            "min": min([x for x in vals if low <= x <= up] or vals),
                            "q1": q1,
                            "median": med,
                            "q3": q3,
                            "max": max([x for x in vals if low <= x <= up] or vals),
                        }
                    )
            boxplots["income_by_employment"] = box_data

        if is_mapped("age") and is_mapped("marital_status"):
            age_by_marital = {}
            for b in borrowers:
                if b.age is not None:
                    mar = b.marital_status or "Unknown"
                    if mar not in age_by_marital:
                        age_by_marital[mar] = []
                    age_by_marital[mar].append(float(b.age))

            box_data = []
            for mar, vals in age_by_marital.items():
                if len(vals) >= 2:
                    med = calculate_median(vals)
                    q1, q3, low, up = calculate_iqr_bounds(vals)
                    box_data.append(
                        {
                            "group": mar,
                            "min": min([x for x in vals if low <= x <= up] or vals),
                            "q1": q1,
                            "median": med,
                            "q3": q3,
                            "max": max([x for x in vals if low <= x <= up] or vals),
                        }
                    )
            boxplots["age_by_marital_status"] = box_data

        # Segment Risk Heatmap: Cross-tab of Employment vs Income Band showing Default Rate
        heatmaps = {}
        if (
            is_mapped("employment_type")
            and is_mapped("income")
            and (is_mapped("historical_default_flag") or is_mapped("delinquency_days"))
        ):
            cross_tab = {}
            for b in borrowers:
                emp = b.employment_type or "Unknown"
                inc_band = get_income_band_label(b.income)
                b_loans = borrower_loans.get(b.id, [])

                if emp not in cross_tab:
                    cross_tab[emp] = {}
                if inc_band not in cross_tab[emp]:
                    cross_tab[emp][inc_band] = {"default_count": 0, "loans_count": 0}

                stat = cross_tab[emp][inc_band]
                for l in b_loans:
                    stat["loans_count"] += 1
                    is_default = False
                    if l.historical_default_flag is True:
                        is_default = True
                    elif l.delinquency_days is not None and l.delinquency_days > 90:
                        is_default = True
                    if is_default:
                        stat["default_count"] += 1

            heatmap_data = []
            for emp, bands_dict in cross_tab.items():
                for band, counts in bands_dict.items():
                    d_rate = (
                        (counts["default_count"] / counts["loans_count"]) * 100.0 if counts["loans_count"] > 0 else 0.0
                    )
                    heatmap_data.append(
                        {"x": emp, "y": band, "value": round(d_rate, 2), "loans_count": counts["loans_count"]}
                    )
            heatmaps["employment_vs_income_risk"] = heatmap_data

        # Segment comparison matrix
        segment_comparison_matrix = []
        for seg_type, segments in borrower_segment_stats.items():
            mapped_check = seg_type
            if seg_type == "age_band":
                mapped_check = "age"
            elif seg_type == "income_band":
                mapped_check = "income"

            if is_mapped(mapped_check):
                for seg_name, val in segments.items():
                    d_rate = (val["default_count"] / val["loans_count"]) * 100.0 if val["loans_count"] > 0 else 0.0
                    segment_comparison_matrix.append(
                        {
                            "segment_type": seg_type,
                            "segment_name": seg_name,
                            "borrower_count": val["count"],
                            "loan_count": val["loans_count"],
                            "total_exposure": round(val["exposure"], 2),
                            "default_rate": round(d_rate, 2),
                        }
                    )

        return {
            "borrower_count": borrower_count,
            "income_distribution": income_distribution,
            "income_bands": income_bands,
            "employment_distribution": employment_distribution,
            "age_bands": age_bands,
            "occupation_distribution": occupation_distribution,
            "education_distribution": education_distribution,
            "marital_status_distribution": marital_status_distribution,
            "region_distribution": region_distribution,
            "family_size_distribution": family_size_distribution,
            "risk_by_borrower_segment": risk_by_borrower_segment,
            "exposure_by_borrower_segment": exposure_by_borrower_segment,
            "visualizations": {
                "bar_charts": bar_charts,
                "stacked_bars": stacked_bars,
                "histograms": histograms,
                "boxplots": boxplots,
                "heatmaps": heatmaps,
                "segment_comparison_matrix": segment_comparison_matrix,
            },
        }
