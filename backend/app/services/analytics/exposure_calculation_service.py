import logging
import uuid
from typing import Any, Dict, Optional

from sqlalchemy import select
from app.models.loan import Loan
from app.models.borrower import Borrower
from app.models.risk_assessment import RiskAssessment
from app.models.dataset import Dataset
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class ExposureCalculationService:
    """
    Centralized service for executing portfolio/loan exposure calculations.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _build_query(
        self,
        dataset_id: uuid.UUID,
        version_id: Optional[uuid.UUID],
        filters: Optional[Dict[str, Any]] = None
    ):
        """
        Helper method to construct a query that selects Loan, Borrower, and RiskAssessment
        with appropriate joins and filters.
        """
        stmt = select(Loan, Borrower, RiskAssessment)
        stmt = stmt.join(Borrower, Loan.borrower_id == Borrower.id, isouter=True)
        stmt = stmt.join(RiskAssessment, Loan.id == RiskAssessment.loan_id, isouter=True)

        stmt = stmt.where(Loan.dataset_id == dataset_id)
        if version_id:
            stmt = stmt.where(Loan.version_id == version_id)

        if filters:
            for key, val in filters.items():
                if val is not None:
                    if isinstance(val, tuple) and len(val) == 2:
                        op, op_val = val
                        target_col = None
                        if hasattr(Loan, key):
                            target_col = getattr(Loan, key)
                        elif hasattr(Borrower, key):
                            target_col = getattr(Borrower, key)
                        elif key == "risk_category":
                            target_col = RiskAssessment.risk_category

                        if target_col is not None:
                            if op in (">", "gt"):
                                stmt = stmt.where(target_col > op_val)
                            elif op in (">=", "gte"):
                                stmt = stmt.where(target_col >= op_val)
                            elif op in ("<", "lt"):
                                stmt = stmt.where(target_col < op_val)
                            elif op in ("<=", "lte"):
                                stmt = stmt.where(target_col <= op_val)
                            elif op in ("!=", "ne"):
                                stmt = stmt.where(target_col != op_val)
                            else:
                                stmt = stmt.where(target_col == op_val)
                    else:
                        if hasattr(Loan, key):
                            stmt = stmt.where(getattr(Loan, key) == val)
                        elif hasattr(Borrower, key):
                            stmt = stmt.where(getattr(Borrower, key) == val)
                        elif key == "risk_category":
                            stmt = stmt.where(RiskAssessment.risk_category == val)

        return stmt

    async def calculate_total_exposure(
        self,
        dataset_id: uuid.UUID,
        filters: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        Calculates the null-safe sum of outstanding loan balances (outstanding_amount)
        for a given dataset (filtering by active version).
        """
        # Resolve dataset and active version
        dataset_stmt = select(Dataset).where(Dataset.id == dataset_id)
        dataset_res = await self.db.execute(dataset_stmt)
        dataset = dataset_res.scalar_one_or_none()
        if not dataset:
            raise ValueError(f"Dataset with ID {dataset_id} not found")

        version_id = dataset.active_version_id
        stmt = await self._build_query(dataset_id, version_id, filters=filters)
        res = await self.db.execute(stmt)
        records = res.all()

        total_exposure = 0.0
        null_count = 0

        for loan, borrower, risk_assessment in records:
            val = loan.outstanding_amount
            if val is None:
                null_count += 1
                exposure_val = float(loan.loan_amount or 0.0)
            else:
                exposure_val = float(val)
            total_exposure += exposure_val

        logger.info(
            "Centralized exposure calculation for dataset %s completed. "
            "Total outstanding exposure: %f. Records with null exposure-relevant field: %d.",
            dataset_id,
            total_exposure,
            null_count
        )
        return total_exposure

    async def calculate_exposure_by_dimension(
        self,
        dataset_id: uuid.UUID,
        dimension: str,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, float]:
        """
        Groups exposure sum (outstanding_amount) by a specified dimension
        (e.g., region, risk_category, loan_status, loan_purpose).
        """
        # Resolve dataset and active version
        dataset_stmt = select(Dataset).where(Dataset.id == dataset_id)
        dataset_res = await self.db.execute(dataset_stmt)
        dataset = dataset_res.scalar_one_or_none()
        if not dataset:
            raise ValueError(f"Dataset with ID {dataset_id} not found")

        version_id = dataset.active_version_id
        stmt = await self._build_query(dataset_id, version_id, filters=filters)
        res = await self.db.execute(stmt)
        records = res.all()

        groups: Dict[str, float] = {}
        null_count = 0

        for loan, borrower, risk_assessment in records:
            val = loan.outstanding_amount
            if val is None:
                null_count += 1
                exposure_val = float(loan.loan_amount or 0.0)
            else:
                exposure_val = float(val)

            # Resolve the dimension value
            dim_val = None
            if dimension == "income_band":
                income = borrower.income if borrower else None
                if income is None:
                    dim_val = "Under $30k"
                elif income < 30000:
                    dim_val = "Under $30k"
                elif income < 60000:
                    dim_val = "$30k - $60k"
                elif income < 100000:
                    dim_val = "$60k - $100k"
                elif income < 150000:
                    dim_val = "$100k - $150k"
                else:
                    dim_val = "$150k+"
            elif hasattr(Loan, dimension):
                dim_val = getattr(loan, dimension)
            elif hasattr(Borrower, dimension):
                dim_val = getattr(borrower, dimension) if borrower else None
            elif dimension == "risk_category":
                dim_val = risk_assessment.risk_category if risk_assessment else None
                if dim_val and hasattr(dim_val, "value"):
                    dim_val = dim_val.value

            dim_str = str(dim_val) if dim_val is not None else "Unknown"
            if dimension == "region" and (dim_str in ("Unknown", "N/A", "None", "") or dim_val is None):
                dim_str = "Unknown Region"
            groups[dim_str] = groups.get(dim_str, 0.0) + exposure_val

        logger.info(
            "Centralized dimension exposure calculation for dataset %s on dimension %s completed. "
            "Groups: %s. Records with null exposure-relevant field: %d.",
            dataset_id,
            dimension,
            groups,
            null_count
        )
        return groups
