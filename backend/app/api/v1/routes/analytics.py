import uuid
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.diagnostic_engine import DiagnosticEngine
from app.core.database import get_db
from app.core.deps import require_any_role
from app.models.risk_assessment import RiskAssessment
from app.models.risk_driver_breakdown import RiskDriverBreakdown
from app.models.user import User
from app.responses.envelope import ResponseEnvelope, build_success_response
from app.schemas.analytics import RiskAssessmentResponse, RiskDriverBreakdownSchema
from app.schemas.dashboard import RiskDashboardResponse
from app.services.analytics_service import AnalyticsService
from app.services.dashboard_service import DashboardService
from app.services.dataset_service import DatasetService

router = APIRouter()


async def get_active_version(db: AsyncSession, dataset_id: uuid.UUID, user: User) -> uuid.UUID:
    """Helper to resolve a dataset's active version ID or raise a 400."""
    dataset_service = DatasetService(db, user)
    dataset = await dataset_service.get_dataset(dataset_id)
    if not dataset.active_version_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Dataset does not have an active version.")
    return dataset.active_version_id


@router.get("/dashboard", response_model=ResponseEnvelope[RiskDashboardResponse])
async def get_risk_dashboard(db: AsyncSession = Depends(get_db), current_user: User = Depends(require_any_role)):
    """
    Calculates cohorted credit portfolio metrics and dashboard highlights.
    """
    service = DashboardService(db)
    data = await service.get_risk_dashboard_data()
    return build_success_response(
        data=RiskDashboardResponse(**data), message="Risk dashboard metrics retrieved successfully."
    )


@router.get("/data-quality", response_model=ResponseEnvelope[Dict[str, Any]])
async def get_data_quality(
    dataset_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_any_role)
):
    """
    Computes data quality scores, drift indicators, and formatting issues.
    """
    version_id = await get_active_version(db, dataset_id, current_user)
    service = AnalyticsService(db, current_user)
    metrics = await service.get_data_quality_analytics(dataset_id, version_id)
    return build_success_response(data=metrics, message="Data quality analytics retrieved successfully.")


@router.get("/borrowers", response_model=ResponseEnvelope[Dict[str, Any]])
async def get_borrower_analytics(
    dataset_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_any_role)
):
    """
    Computes demographic segment risk defaults and exposure distributions.
    """
    version_id = await get_active_version(db, dataset_id, current_user)
    service = AnalyticsService(db, current_user)
    metrics = await service.get_borrower_analytics(dataset_id, version_id)
    return build_success_response(data=metrics, message="Borrower analytics retrieved successfully.")


@router.get("/loans", response_model=ResponseEnvelope[Dict[str, Any]])
async def get_loan_analytics(
    dataset_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_any_role)
):
    """
    Computes loan size stats, outstanding default waterfall, and DPD delinquency aging buckets.
    """
    version_id = await get_active_version(db, dataset_id, current_user)
    service = AnalyticsService(db, current_user)
    metrics = await service.get_loan_analytics(dataset_id, version_id)
    return build_success_response(data=metrics, message="Loan analytics retrieved successfully.")


@router.get("/risk", response_model=ResponseEnvelope[List[RiskAssessmentResponse]])
async def get_risk_assessments(
    dataset_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_any_role)
):
    """
    Retrieves detailed credit risk assessment output records for loans in a dataset.
    """
    version_id = await get_active_version(db, dataset_id, current_user)

    stmt = select(RiskAssessment).where(
        RiskAssessment.dataset_id == dataset_id, RiskAssessment.version_id == version_id
    )
    res = await db.execute(stmt)
    assessments = res.scalars().all()

    responses = [
        RiskAssessmentResponse(
            id=a.id,
            dataset_id=a.dataset_id,
            version_id=a.version_id,
            borrower_id=a.borrower_id,
            loan_id=a.loan_id,
            risk_score=a.risk_score,
            risk_category=a.risk_category,
            risk_driver_summary=a.risk_driver_summary,
            assessment_version=a.assessment_version,
            rule_set_version=a.rule_set_version,
            created_at=a.created_at,
        )
        for a in assessments
    ]

    return build_success_response(data=responses, message="Risk assessments retrieved successfully.")


@router.get("/risk/drivers", response_model=ResponseEnvelope[List[RiskDriverBreakdownSchema]])
async def get_risk_drivers(
    dataset_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_any_role)
):
    """
    Retrieves granular weights and scores breakdown details for risk assessors.
    """
    version_id = await get_active_version(db, dataset_id, current_user)

    stmt = (
        select(RiskDriverBreakdown)
        .join(RiskAssessment)
        .where(RiskAssessment.dataset_id == dataset_id, RiskAssessment.version_id == version_id)
    )
    res = await db.execute(stmt)
    drivers = res.scalars().all()

    responses = [
        RiskDriverBreakdownSchema(
            driver_name=d.driver_name,
            driver_value=d.driver_value,
            driver_weight=d.driver_weight,
            contribution_score=d.contribution_score,
            explanation=d.explanation,
        )
        for d in drivers
    ]
    return build_success_response(data=responses, message="Risk assessment drivers breakdown retrieved successfully.")


@router.get("/portfolio", response_model=ResponseEnvelope[Dict[str, Any]])
async def get_portfolio_analytics(
    dataset_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_any_role)
):
    """
    Retrieves portfolio overall KPIs and exposure segment slices.
    """
    version_id = await get_active_version(db, dataset_id, current_user)
    service = AnalyticsService(db, current_user)
    metrics = await service.get_portfolio_analytics(dataset_id, version_id)
    return build_success_response(data=metrics, message="Portfolio analytics retrieved successfully.")


@router.get("/concentration", response_model=ResponseEnvelope[Dict[str, Any]])
async def get_concentration_analytics(
    dataset_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_any_role)
):
    """
    Retrieves HHI indexes and exposure segments ranked tables.
    """
    version_id = await get_active_version(db, dataset_id, current_user)
    service = AnalyticsService(db, current_user)
    metrics = await service.get_concentration_analytics(dataset_id, version_id)
    return build_success_response(data=metrics, message="Portfolio concentration analytics retrieved successfully.")


@router.get("/trends", response_model=ResponseEnvelope[Dict[str, Any]])
async def get_trend_analytics(
    dataset_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_any_role)
):
    """
    Retrieves monthly time-series analytics (growth, exposure, delinquency, risk).
    """
    version_id = await get_active_version(db, dataset_id, current_user)
    service = AnalyticsService(db, current_user)
    metrics = await service.get_trend_analytics(dataset_id, version_id)
    return build_success_response(data=metrics, message="Portfolio trend analytics retrieved successfully.")


@router.get("/vintage", response_model=ResponseEnvelope[Dict[str, Any]])
async def get_vintage_analytics(
    dataset_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_any_role)
):
    """
    Retrieves cohorted vintage tables and matrices grouped by disbursement quarter.
    """
    version_id = await get_active_version(db, dataset_id, current_user)
    service = AnalyticsService(db, current_user)
    metrics = await service.get_vintage_analytics(dataset_id, version_id)
    return build_success_response(data=metrics, message="Portfolio vintage analytics retrieved successfully.")


@router.get("/migration", response_model=ResponseEnvelope[Dict[str, Any]])
async def get_migration_analytics(
    dataset_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_any_role)
):
    """
    Retrieves transition count and exposure matrices comparing current version with historical baseline.
    """
    version_id = await get_active_version(db, dataset_id, current_user)
    service = AnalyticsService(db, current_user)
    metrics = await service.get_migration_analytics(dataset_id, version_id)
    return build_success_response(data=metrics, message="Portfolio risk migration analytics retrieved successfully.")


@router.get("/diagnostics", response_model=ResponseEnvelope[Dict[str, Any]])
async def get_diagnostics(
    dataset_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_any_role)
):
    """
    Retrieves segment comparisons, correlation matrices, and root-cause analysis indicators.
    """
    version_id = await get_active_version(db, dataset_id, current_user)
    engine = DiagnosticEngine(db)
    metrics = await engine.get_metrics(dataset_id, version_id)
    return build_success_response(data=metrics, message="Diagnostics analytics retrieved successfully.")
