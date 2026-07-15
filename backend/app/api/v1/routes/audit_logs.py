from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.audit_log import AuditLog
from app.models.user import User
from app.responses.envelope import ResponseEnvelope, build_success_response
from app.schemas.audit_log import AuditLogListResponse, AuditLogResponse
from app.services.audit_log_service import AuditLogService

router = APIRouter()


@router.get("/my-activity", response_model=ResponseEnvelope[AuditLogListResponse])
async def get_my_activity(
    skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """
    Fetches the active user's personal operations audit logs feed.
    """
    service = AuditLogService(db, current_user)
    logs = await service.get_my_activity(skip=skip, limit=limit)

    total_stmt = select(func.count()).select_from(AuditLog).where(AuditLog.user_id == current_user.id)
    total = (await db.execute(total_stmt)).scalar() or 0

    responses = [
        AuditLogResponse(
            id=l.id,
            user_id=l.user_id,
            request_id=l.request_id,
            action=l.action,
            module_name=l.module_name,
            resource_type=l.resource_type,
            resource_id=l.resource_id,
            ip_address=l.ip_address,
            user_agent=l.user_agent,
            details=l.details_json,
            created_at=l.created_at,
        )
        for l in logs
    ]

    return build_success_response(
        data=AuditLogListResponse(items=responses, total=total),
        message="Personal activity audit logs retrieved successfully.",
    )
