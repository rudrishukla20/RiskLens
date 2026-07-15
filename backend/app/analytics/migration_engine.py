import uuid
from typing import Any, Dict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.borrower import Borrower
from app.models.dataset_version import DatasetVersion
from app.models.loan import Loan
from app.models.risk_assessment import RiskAssessment


class MigrationEngine:
    """
    Deterministic risk migration analytics engine.
    Calculates movements of borrowers' credit risk categories between dataset versions.
    Handles single-version data gracefully by offering a descriptive fallback state.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _get_cat_str(self, cat: Any) -> str:
        if cat is None:
            return "LOW"
        return cat.value if hasattr(cat, "value") else str(cat)

    async def get_metrics(self, dataset_id: uuid.UUID, version_id: uuid.UUID) -> Dict[str, Any]:
        """
        Computes transition metrics between the current version and a previous dataset version.
        """
        # Find all versions for this dataset to determine previous version
        version_stmt = (
            select(DatasetVersion)
            .where(DatasetVersion.dataset_id == dataset_id)
            .order_by(DatasetVersion.version_number)
        )
        versions_res = await self.session.execute(version_stmt)
        versions = list(versions_res.scalars().all())

        if len(versions) < 2:
            return self._build_unavailable_response(
                "unavailable: multiple versions are required to compute risk migration trends"
            )

        # Identify current and previous version object
        curr_ver = next((v for v in versions if v.id == version_id), None)
        if not curr_ver:
            return self._build_unavailable_response("unavailable: current version not found")

        # Previous version is the version with the highest version_number lower than the current version
        prev_versions = [v for v in versions if v.version_number < curr_ver.version_number]
        if not prev_versions:
            return self._build_unavailable_response("unavailable: no historical baseline version found")

        prev_ver = prev_versions[-1]  # closest previous version

        # Get risk assessments for previous version
        prev_stmt = (
            select(RiskAssessment, Borrower)
            .join(Borrower, RiskAssessment.borrower_id == Borrower.id)
            .where(RiskAssessment.dataset_id == dataset_id, RiskAssessment.version_id == prev_ver.id)
        )
        prev_res = await self.session.execute(prev_stmt)
        prev_assess = prev_res.all()

        # Get risk assessments for current version
        curr_stmt = (
            select(RiskAssessment, Borrower, Loan)
            .join(Borrower, RiskAssessment.borrower_id == Borrower.id)
            .join(Loan, RiskAssessment.loan_id == Loan.id)
            .where(RiskAssessment.dataset_id == dataset_id, RiskAssessment.version_id == version_id)
        )
        curr_res = await self.session.execute(curr_stmt)
        curr_assess = curr_res.all()

        if not prev_assess or not curr_assess:
            return self._build_unavailable_response(
                "unavailable: risk assessments not run on both current and baseline versions"
            )

        # Map source_borrower_id -> risk_category
        prev_map = {}
        for ass, b in prev_assess:
            if b.source_borrower_id:
                prev_map[b.source_borrower_id] = ass.risk_category

        # Map source_borrower_id -> current assessment info
        curr_map = {}
        for ass, b, l in curr_assess:
            if b.source_borrower_id:
                curr_map[b.source_borrower_id] = {
                    "category": ass.risk_category,
                    "exposure": l.outstanding_amount or 0.0,
                }

        # Initialize matrix grid
        categories = ["LOW", "MEDIUM", "HIGH"]
        matrix_counts = {from_cat: {to_cat: 0 for to_cat in categories} for from_cat in categories}
        matrix_exposure = {from_cat: {to_cat: 0.0 for to_cat in categories} for from_cat in categories}

        migrated_borrowers = 0
        total_matched = 0

        for b_id, prev_cat in prev_map.items():
            if b_id in curr_map:
                total_matched += 1
                curr_info = curr_map[b_id]
                curr_cat = curr_info["category"]
                exp = curr_info["exposure"]

                from_str = self._get_cat_str(prev_cat)
                to_str = self._get_cat_str(curr_cat)

                if from_str in categories and to_str in categories:
                    matrix_counts[from_str][to_str] += 1
                    matrix_exposure[from_str][to_str] += exp
                    if from_str != to_str:
                        migrated_borrowers += 1

        if total_matched == 0:
            return self._build_unavailable_response("unavailable: no common borrowers matched across versions")

        # Format to list for database persistence
        cells_to_persist = []
        period_start_date = prev_ver.created_at.date() if prev_ver.created_at else None
        period_end_date = curr_ver.created_at.date() if curr_ver.created_at else None

        for from_cat in categories:
            for to_cat in categories:
                cells_to_persist.append(
                    {
                        "from_risk_category": from_cat,
                        "to_risk_category": to_cat,
                        "borrower_count": matrix_counts[from_cat][to_cat],
                        "exposure_amount": matrix_exposure[from_cat][to_cat],
                        "period_start": period_start_date,
                        "period_end": period_end_date,
                    }
                )

        # Format visualization payloads (e.g. Sankey chart)
        sankey_nodes = [{"name": c} for c in categories]  # Source nodes
        sankey_nodes.extend([{"name": f"{c} (Current)"} for c in categories])

        sankey_links = []
        for i, from_cat in enumerate(categories):
            for j, to_cat in enumerate(categories):
                count = matrix_counts[from_cat][to_cat]
                if count > 0:
                    sankey_links.append(
                        {"source": i, "target": j + 3, "value": count, "exposure": matrix_exposure[from_cat][to_cat]}
                    )

        return {
            "status": "success",
            "cells_list": cells_to_persist,  # Helper for service database insertion
            "visualizations": {
                "migration_matrix": {
                    "from_categories": categories,
                    "to_categories": categories,
                    "counts": [[matrix_counts[fc][tc] for tc in categories] for fc in categories],
                    "exposures": [[matrix_exposure[fc][tc] for tc in categories] for fc in categories],
                },
                "sankey_diagram": {"nodes": sankey_nodes, "links": sankey_links},
                "migration_summary_cards": {
                    "total_matched_borrowers": total_matched,
                    "migrated_borrowers_count": migrated_borrowers,
                    "migration_rate_percentage": (
                        round((migrated_borrowers / total_matched) * 100, 2) if total_matched else 0.0
                    ),
                },
            },
        }

    def _build_unavailable_response(self, reason: str) -> Dict[str, Any]:
        categories = ["LOW", "MEDIUM", "HIGH"]
        return {
            "status": "unavailable",
            "message": reason,
            "cells_list": [],
            "visualizations": {
                "migration_matrix": {
                    "from_categories": categories,
                    "to_categories": categories,
                    "counts": [[0, 0, 0], [0, 0, 0], [0, 0, 0]],
                    "exposures": [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]],
                },
                "sankey_diagram": {"nodes": [], "links": []},
                "migration_summary_cards": {
                    "total_matched_borrowers": 0,
                    "migrated_borrowers_count": 0,
                    "migration_rate_percentage": 0.0,
                },
            },
        }

    def _build_empty_response(self, dataset_id: uuid.UUID, version_id: uuid.UUID) -> Dict[str, Any]:
        return self._build_unavailable_response("unavailable: dataset is empty")
