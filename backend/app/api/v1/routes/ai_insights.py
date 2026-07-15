import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_any_role
from app.core.rate_limit import LIMIT_AI, limiter
from app.models.ai_insight import AIInsight
from app.models.user import User
from app.responses.envelope import ResponseEnvelope, build_success_response
from app.schemas.ai_insight import (
    AIInsightGenerateRequest,
    AIInsightListResponse,
    AIInsightResponse,
)
from app.services.ai_insight_service import AIInsightService
from app.services.dataset_service import DatasetService

router = APIRouter()


@router.post("/generate", response_model=ResponseEnvelope[AIInsightResponse])
@limiter.limit(LIMIT_AI)
async def generate_ai_insight(
    request: Request,
    body: AIInsightGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_any_role),
):
    """
    Executes AI LLM insight generation run or returns cached results.
    """
    service = AIInsightService(db, current_user)

    # 1. Cache hit check if not forced regenerate
    if not body.force_regenerate:
        cached = await service.repo.get_latest_by_type(
            analysis_type=body.analysis_type, dataset_id=body.dataset_id, document_id=body.document_id
        )
        if cached:
            data = AIInsightResponse(
                id=cached.id,
                dataset_id=cached.dataset_id,
                document_id=cached.document_id,
                analysis_type=cached.analysis_type,
                executive_summary=cached.executive_summary,
                key_findings=cached.key_findings_json,
                risk_observations=cached.risk_observations_json,
                recommendations=cached.recommendations_json,
                source_metrics=cached.source_metrics_json,
                provider=cached.provider,
                model_name=cached.model_name,
                generated_by=cached.generated_by,
                created_at=cached.created_at,
            )
            return build_success_response(data=data, message="AI insights retrieved from cache.")

    # 2. Resolve version_id if dataset is scoped
    version_id = None
    if body.dataset_id:
        dataset_service = DatasetService(db, current_user)
        dataset = await dataset_service.get_dataset(body.dataset_id)
        version_id = dataset.active_version_id
        if not version_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Selected dataset does not have an active version."
            )

    # 3. Generate insight
    insight = await service.generate_insight(
        dataset_id=body.dataset_id,
        version_id=version_id,
        document_id=body.document_id,
        analysis_type=body.analysis_type,
    )
    await db.commit()

    data = AIInsightResponse(
        id=insight.id,
        dataset_id=insight.dataset_id,
        document_id=insight.document_id,
        analysis_type=insight.analysis_type,
        executive_summary=insight.executive_summary,
        key_findings=insight.key_findings_json,
        risk_observations=insight.risk_observations_json,
        recommendations=insight.recommendations_json,
        source_metrics=insight.source_metrics_json,
        provider=insight.provider,
        model_name=insight.model_name,
        generated_by=insight.generated_by,
        created_at=insight.created_at,
    )
    return build_success_response(data=data, message="AI insights generated successfully.")


@router.get("", response_model=ResponseEnvelope[AIInsightListResponse])
async def list_ai_insights(
    dataset_id: Optional[uuid.UUID] = None,
    document_id: Optional[uuid.UUID] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_any_role),
):
    """
    Lists generated AI insights logs.
    """
    service = AIInsightService(db, current_user)

    # Query with filters
    stmt = select(AIInsight)
    if dataset_id:
        stmt = stmt.where(AIInsight.dataset_id == dataset_id)
    if document_id:
        stmt = stmt.where(AIInsight.document_id == document_id)

    total_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(total_stmt)).scalar() or 0

    stmt = stmt.offset(skip).limit(limit).order_by(AIInsight.created_at.desc())
    res = await db.execute(stmt)
    insights = res.scalars().all()

    responses = [
        AIInsightResponse(
            id=i.id,
            dataset_id=i.dataset_id,
            document_id=i.document_id,
            analysis_type=i.analysis_type,
            executive_summary=i.executive_summary,
            key_findings=i.key_findings_json,
            risk_observations=i.risk_observations_json,
            recommendations=i.recommendations_json,
            source_metrics=i.source_metrics_json,
            provider=i.provider,
            model_name=i.model_name,
            generated_by=i.generated_by,
            created_at=i.created_at,
        )
        for i in insights
    ]
    return build_success_response(
        data=AIInsightListResponse(items=responses, total=total), message="AI insights list retrieved successfully."
    )


@router.get("/{insight_id}", response_model=ResponseEnvelope[AIInsightResponse])
async def get_ai_insight(
    insight_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_any_role)
):
    """
    Retrieves detailed AI insight content.
    """
    service = AIInsightService(db, current_user)
    insight = await service.repo.get(insight_id)
    if not insight:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI Insight not found.")

    data = AIInsightResponse(
        id=insight.id,
        dataset_id=insight.dataset_id,
        document_id=insight.document_id,
        analysis_type=insight.analysis_type,
        executive_summary=insight.executive_summary,
        key_findings=insight.key_findings_json,
        risk_observations=insight.risk_observations_json,
        recommendations=insight.recommendations_json,
        source_metrics=insight.source_metrics_json,
        provider=insight.provider,
        model_name=insight.model_name,
        generated_by=insight.generated_by,
        created_at=insight.created_at,
    )
    return build_success_response(data=data, message="AI insight details retrieved successfully.")
