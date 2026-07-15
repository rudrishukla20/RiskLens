import logging
import math
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums.dataset_status import DatasetStatusEnum
from app.ingestion.schema_inferer import _infer_pandas_dtype
from app.models.column_profile import ColumnProfile
from app.models.dataset import Dataset
from app.models.profiling import ProfileRun
from app.models.raw_record import RawRecord
from app.utils.statistics import (
    calculate_correlation_matrix,
    calculate_iqr_bounds,
    calculate_kurtosis,
    calculate_mean,
    calculate_median,
    calculate_percentile,
    calculate_skewness,
    calculate_std_dev,
    detect_outliers_iqr,
    detect_outliers_zscore,
)

logger = logging.getLogger(__name__)


class ProfilingEngine:
    """
    Banking-grade Data Profiling Engine.
    Computes statistical profiles, outlier distributions, missing value counts,
    and histograms for numerical/categorical fields across dataset version files.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def run_profiling(
        self, dataset_id: uuid.UUID, version_id: uuid.UUID, user_id: Optional[uuid.UUID] = None
    ) -> ProfileRun:
        """
        Executes structural profiling across all dataset columns, persisting
        metrics to column_profiles and profile_runs.
        """
        logger.info("Starting data profiling run for dataset_id=%s, version_id=%s", dataset_id, version_id)

        # 1. Create ProfileRun active record
        run = ProfileRun(
            id=uuid.uuid4(),
            dataset_id=dataset_id,
            version_id=version_id,
            status=DatasetStatusEnum.PROFILING,
            started_at=datetime.now(timezone.utc),
            created_by=user_id,
        )
        self.db.add(run)
        await self.db.flush()

        # Update dataset profiling status
        dataset_stmt = select(Dataset).where(Dataset.id == dataset_id)
        dataset_res = await self.db.execute(dataset_stmt)
        dataset = dataset_res.scalar_one_or_none()
        if dataset:
            dataset.profiling_status = DatasetStatusEnum.PROFILING
            self.db.add(dataset)

        # 2. Fetch RawRecords to build pandas DataFrame
        records_stmt = select(RawRecord).where(RawRecord.dataset_id == dataset_id, RawRecord.version_id == version_id)
        records_res = await self.db.execute(records_stmt)
        records = records_res.scalars().all()

        total_rows = len(records)
        if total_rows == 0:
            run.status = DatasetStatusEnum.ANALYZED
            run.row_count = 0
            run.column_count = 0
            run.missing_percentage = 0.0
            run.duplicate_percentage = 0.0
            run.dataset_health_score = 100.0
            run.completed_at = datetime.now(timezone.utc)
            if dataset:
                dataset.profiling_status = DatasetStatusEnum.ANALYZED
            await self.db.flush()
            return run

        # Construct DataFrame
        df = pd.DataFrame([r.raw_data_json for r in records])
        column_count = len(df.columns)

        # 3. Compute ColumnProfiles
        profiles_to_create = []
        total_cells = total_rows * column_count
        total_missing_cells = 0

        # Unique records count
        # For duplicates check, convert unhashable types (dicts/lists) in rows to strings if present,
        # but raw_data_json values are usually flat fields. Let's do string representation comparison:
        df_str = df.astype(str)
        duplicate_rows_count = df_str.duplicated().sum()
        duplicate_percentage = (duplicate_rows_count / total_rows) * 100.0

        for col_name in df.columns:
            series = df[col_name]

            # Count missing cells
            # treats NaN, None, and empty whitespace strings as missing
            col_missing = int(series.isna().sum() + (series.astype(str).str.strip() == "").sum())
            total_missing_cells += col_missing
            col_missing_pct = (col_missing / total_rows) * 100.0

            # Count unique values
            col_unique = int(series.dropna().nunique())

            # Infer type
            inferred_type = _infer_pandas_dtype(series)

            # Initialize stats
            mean_val = None
            median_val = None
            min_val = None
            max_val = None
            std_val = None
            p25_val = None
            p75_val = None
            col_outliers = 0
            dist_json = {}

            # Attempt numeric conversion for statistical calculations if type is numeric
            if inferred_type in ("integer", "float"):
                num_series = pd.to_numeric(series, errors="coerce").dropna()
                if not num_series.empty:
                    min_val = float(num_series.min())
                    max_val = float(num_series.max())
                    mean_val = float(num_series.mean())
                    median_val = float(num_series.median())
                    std_val = float(num_series.std()) if len(num_series) > 1 else 0.0
                    p25_val = float(num_series.quantile(0.25))
                    p75_val = float(num_series.quantile(0.75))

                    # IQR outlier check
                    iqr = p75_val - p25_val
                    lower_bound = p25_val - 1.5 * iqr
                    upper_bound = p75_val + 1.5 * iqr
                    col_outliers = int(((num_series < lower_bound) | (num_series > upper_bound)).sum())

                    # Histogram generation using numpy
                    try:
                        counts, bin_edges = np.histogram(num_series, bins=10)
                        buckets = []
                        for idx in range(len(counts)):
                            buckets.append(f"{round(float(bin_edges[idx]), 2)} - {round(float(bin_edges[idx+1]), 2)}")
                        dist_json = {"type": "numeric", "buckets": buckets, "counts": counts.tolist()}
                    except Exception as e:
                        logger.warning("Failed to generate histogram for column %s: %s", col_name, e)

            # Categorical frequency distribution fallback
            if not dist_json:
                # String/boolean categories distribution (top 10 categories)
                v_counts = series.dropna().value_counts().head(10)
                categories = [str(k) for k in v_counts.index]
                counts = [int(v) for v in v_counts.values]
                dist_json = {"type": "categorical", "categories": categories, "counts": counts}

            # Helper method to safe-convert NaN/Inf values to None
            def sanitize_float(v: Optional[float]) -> Optional[float]:
                if v is None or math.isnan(v) or math.isinf(v):
                    return None
                return v

            profile = ColumnProfile(
                id=uuid.uuid4(),
                profile_run_id=run.id,
                dataset_id=dataset_id,
                column_name=str(col_name),
                data_type=inferred_type,
                missing_count=col_missing,
                missing_percentage=round(col_missing_pct, 2),
                unique_count=col_unique,
                mean_value=sanitize_float(mean_val),
                median_value=sanitize_float(median_val),
                min_value=sanitize_float(min_val),
                max_value=sanitize_float(max_val),
                std_dev=sanitize_float(std_val),
                percentile_25=sanitize_float(p25_val),
                percentile_75=sanitize_float(p75_val),
                outlier_count=col_outliers,
                distribution_json=dist_json,
            )
            profiles_to_create.append(profile)

        # 4. Save ColumnProfiles in batches
        for i in range(0, len(profiles_to_create), 500):
            batch = profiles_to_create[i : i + 500]
            self.db.add_all(batch)
            await self.db.flush()

        # 5. Calculate global metrics
        global_missing_pct = (total_missing_cells / total_cells) * 100.0 if total_cells > 0 else 0.0
        # Health score: simple weighted index penalizing missing cells & duplicates
        health_score = 100.0 - (global_missing_pct * 0.7 + duplicate_percentage * 0.3)
        health_score = max(0.0, min(100.0, health_score))

        # Update run stats
        run.row_count = total_rows
        run.column_count = column_count
        run.missing_percentage = round(global_missing_pct, 2)
        run.duplicate_percentage = round(duplicate_percentage, 2)
        run.dataset_health_score = round(health_score, 2)
        run.status = DatasetStatusEnum.ANALYZED
        run.completed_at = datetime.now(timezone.utc)
        self.db.add(run)

        # Update dataset profiling status
        if dataset:
            dataset.profiling_status = DatasetStatusEnum.ANALYZED
            # If upload status was UPLOADED, let's mark it as ANALYZED as well
            if dataset.upload_status == DatasetStatusEnum.UPLOADED:
                dataset.upload_status = DatasetStatusEnum.ANALYZED
            self.db.add(dataset)

        logger.info(
            "Profiling run completed for dataset_id=%s. Health Score: %s, Status: %s. Columns profiled: %d",
            dataset_id,
            run.dataset_health_score,
            DatasetStatusEnum.ANALYZED,
            column_count,
        )
        return run

    async def get_metrics(self, dataset_id: uuid.UUID, version_id: uuid.UUID) -> Dict[str, Any]:
        """
        Retrieves complete computed metrics and visualizations structure for
        Dataset Profiling.
        """
        logger.info("Computing Dataset Profiling metrics for dataset_id=%s, version_id=%s", dataset_id, version_id)

        # 1. Fetch RawRecords
        records_stmt = (
            select(RawRecord)
            .where(RawRecord.dataset_id == dataset_id, RawRecord.version_id == version_id)
            .order_by(RawRecord.source_row_number.asc())
        )
        records_res = await self.db.execute(records_stmt)
        records = list(records_res.scalars().all())
        total_rows = len(records)

        if total_rows == 0:
            return {
                "rows": 0,
                "columns": 0,
                "data_types": {},
                "numeric_statistics": {},
                "categorical_distributions": {},
                "missing_percentage": {},
                "uniqueness": {},
                "outliers": {},
                "percentiles": {},
                "correlation_matrix": {"columns": [], "matrix": []},
                "skewness": {},
                "kurtosis": {},
                "visualizations": {
                    "histograms": {},
                    "boxplots": {},
                    "distribution_charts": {},
                    "correlation_heatmap": {},
                    "profile_table": [],
                    "column_health_cards": {},
                },
            }

        # 2. Build DataFrame
        df = pd.DataFrame([r.raw_data_json for r in records])
        column_count = len(df.columns)

        data_types = {}
        numeric_statistics = {}
        categorical_distributions = {}
        missing_percentage = {}
        uniqueness = {}
        outliers = {}
        percentiles = {}
        skewness = {}
        kurtosis = {}

        histograms = {}
        boxplots = {}
        distribution_charts = {}
        column_health_cards = {}
        profile_table = []

        numeric_col_names = []
        numeric_col_data = []

        for col_name in df.columns:
            series = df[col_name]

            # Count missing
            col_missing = int(series.isna().sum() + (series.astype(str).str.strip() == "").sum())
            col_missing_pct = (col_missing / total_rows) * 100.0
            missing_percentage[col_name] = round(col_missing_pct, 2)

            # Uniqueness
            col_unique = int(series.dropna().nunique())
            uniqueness[col_name] = {
                "unique_count": col_unique,
                "unique_percentage": round((col_unique / total_rows) * 100.0, 2),
            }

            # Infer data type
            inferred_type = _infer_pandas_dtype(series)
            data_types[col_name] = inferred_type

            table_row = {
                "column_name": col_name,
                "data_type": inferred_type,
                "missing_count": col_missing,
                "missing_percentage": round(col_missing_pct, 2),
                "unique_count": col_unique,
                "mean": None,
                "median": None,
                "std_dev": None,
            }

            is_numeric = False
            if inferred_type in ("integer", "float"):
                num_series = pd.to_numeric(series, errors="coerce").dropna()
                if not num_series.empty:
                    is_numeric = True
                    vals = num_series.tolist()

                    mean_val = calculate_mean(vals)
                    median_val = calculate_median(vals)
                    std_val = calculate_std_dev(vals, mean_val)

                    table_row["mean"] = round(mean_val, 4)
                    table_row["median"] = round(median_val, 4)
                    table_row["std_dev"] = round(std_val, 4)

                    p5 = calculate_percentile(vals, 5)
                    p25 = calculate_percentile(vals, 25)
                    p50 = calculate_percentile(vals, 50)
                    p75 = calculate_percentile(vals, 75)
                    p95 = calculate_percentile(vals, 95)
                    percentiles[col_name] = {
                        "p5": round(p5, 4),
                        "p25": round(p25, 4),
                        "p50": round(p50, 4),
                        "p75": round(p75, 4),
                        "p95": round(p95, 4),
                    }

                    skew_val = calculate_skewness(vals)
                    kurt_val = calculate_kurtosis(vals)
                    skewness[col_name] = round(skew_val, 4) if skew_val is not None else None
                    kurtosis[col_name] = round(kurt_val, 4) if kurt_val is not None else None

                    q1, q3, lower, upper = calculate_iqr_bounds(vals)
                    iqr_outlier_flags = detect_outliers_iqr(vals)
                    iqr_outlier_count = sum(iqr_outlier_flags)

                    z_outlier_flags = detect_outliers_zscore(vals)
                    z_outlier_count = sum(z_outlier_flags)

                    outliers[col_name] = {
                        "iqr_method": {
                            "outlier_count": iqr_outlier_count,
                            "outlier_percentage": round((iqr_outlier_count / len(vals)) * 100.0, 2) if vals else 0.0,
                            "lower_bound": round(lower, 4),
                            "upper_bound": round(upper, 4),
                        },
                        "zscore_method": {
                            "outlier_count": z_outlier_count,
                            "outlier_percentage": round((z_outlier_count / len(vals)) * 100.0, 2) if vals else 0.0,
                        },
                    }

                    numeric_statistics[col_name] = {
                        "min": min(vals),
                        "max": max(vals),
                        "mean": round(mean_val, 4),
                        "median": round(median_val, 4),
                        "std_dev": round(std_val, 4),
                        "iqr": round(q3 - q1, 4),
                        "skewness": round(skew_val, 4) if skew_val is not None else None,
                        "kurtosis": round(kurt_val, 4) if kurt_val is not None else None,
                    }

                    try:
                        counts, bin_edges = np.histogram(vals, bins=10)
                        histograms[col_name] = {
                            "counts": counts.tolist(),
                            "bins": [
                                f"{round(float(bin_edges[idx]), 2)} - {round(float(bin_edges[idx+1]), 2)}"
                                for idx in range(len(counts))
                            ],
                        }
                    except Exception as e:
                        logger.warning("Failed to generate histogram for %s: %s", col_name, e)

                    normal_vals = [x for x in vals if lower <= x <= upper]
                    min_norm = min(normal_vals) if normal_vals else min(vals)
                    max_norm = max(normal_vals) if normal_vals else max(vals)
                    boxplots[col_name] = {
                        "min": min_norm,
                        "q1": q1,
                        "median": median_val,
                        "q3": q3,
                        "max": max_norm,
                        "outlier_count": iqr_outlier_count,
                        "outliers": [float(x) for x in vals if x < lower or x > upper][:50],
                    }

                    numeric_col_names.append(col_name)
                    series_num = pd.to_numeric(series, errors="coerce")
                    mean_impute = series_num.mean()
                    filled = series_num.fillna(mean_impute if not pd.isna(mean_impute) else 0.0)
                    numeric_col_data.append(filled.tolist())

                    distribution_charts[col_name] = {"type": "numeric", "data": histograms.get(col_name, {})}

            if not is_numeric:
                v_counts = series.dropna().value_counts().head(10)
                categories = [str(k) for k in v_counts.index]
                counts = [int(v) for v in v_counts.values]
                categorical_distributions[col_name] = {"categories": categories, "counts": counts}

                distribution_charts[col_name] = {
                    "type": "categorical",
                    "data": {"categories": categories, "counts": counts},
                }

            dup_pct = (1.0 - (col_unique / total_rows)) * 100.0 if col_unique > 0 else 0.0
            col_health = 100.0 - (col_missing_pct * 0.7 + min(100.0, dup_pct) * 0.3)
            col_health = round(max(0.0, min(100.0, col_health)), 2)

            column_health_cards[col_name] = {
                "missing_percentage": round(col_missing_pct, 2),
                "unique_percentage": round((col_unique / total_rows) * 100.0, 2),
                "health_score": col_health,
                "alerts": [
                    "High missing percentage (>10%)" if col_missing_pct > 10 else None,
                    "Potential duplicate issues" if dup_pct > 50 and col_unique > 1 else None,
                ],
            }
            column_health_cards[col_name]["alerts"] = [
                a for a in column_health_cards[col_name]["alerts"] if a is not None
            ]

            profile_table.append(table_row)

        corr_matrix_viz = {"columns": [], "matrix": []}
        if len(numeric_col_names) > 1:
            try:
                corr_mat = calculate_correlation_matrix(numeric_col_data)
                rounded_corr_mat = [[round(x, 4) for x in row] for row in corr_mat]
                corr_matrix_viz = {"columns": numeric_col_names, "matrix": rounded_corr_mat}
            except Exception as e:
                logger.error("Failed to compute correlation matrix: %s", e)

        return {
            "rows": total_rows,
            "columns": column_count,
            "data_types": data_types,
            "numeric_statistics": numeric_statistics,
            "categorical_distributions": categorical_distributions,
            "missing_percentage": missing_percentage,
            "uniqueness": uniqueness,
            "outliers": outliers,
            "percentiles": percentiles,
            "correlation_matrix": corr_matrix_viz,
            "skewness": skewness,
            "kurtosis": kurtosis,
            "visualizations": {
                "histograms": histograms,
                "boxplots": boxplots,
                "distribution_charts": distribution_charts,
                "correlation_heatmap": corr_matrix_viz,
                "profile_table": profile_table,
                "column_health_cards": column_health_cards,
            },
        }
