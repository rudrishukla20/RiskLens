import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_admin
from app.models.audit_log import AuditLog
from app.models.dataset import Dataset
from app.models.report import Report
from app.models.user import User
from app.responses.envelope import ResponseEnvelope, build_success_response
from app.schemas.audit_log import AuditLogListResponse, AuditLogResponse
from app.schemas.dashboard import AdminDashboardResponse
from app.schemas.dataset import DatasetListResponse, DatasetResponse
from app.schemas.report import ReportListResponse, ReportResponse
from app.services.audit_log_service import SystemAuditLogService
from app.services.dashboard_service import DashboardService
from app.services.dataset_service import DatasetService
from app.services.report_service import ReportService
from app.services.system_setting_service import SystemSettingService

router = APIRouter()


# Schema for settings
class SystemSettingResponse(BaseModel):
    id: uuid.UUID
    setting_key: str
    setting_value: Optional[str] = None
    setting_type: str
    description: Optional[str] = None
    updated_by: Optional[uuid.UUID] = None
    updated_at: datetime

    class Config:
        from_attributes = True


class SystemSettingUpdateRequest(BaseModel):
    setting_value: str = Field(description="New value for the setting")


@router.get("/dashboard", response_model=ResponseEnvelope[AdminDashboardResponse])
async def get_admin_dashboard(db: AsyncSession = Depends(get_db), admin_user: User = Depends(require_admin)):
    """Retrieves system administrative health summary analytics (Admin-only)."""
    service = DashboardService(db)
    data = await service.get_admin_dashboard_data()
    return build_success_response(
        data=AdminDashboardResponse(**data), message="Admin dashboard metrics retrieved successfully."
    )


@router.get("/datasets", response_model=ResponseEnvelope[DatasetListResponse])
async def list_admin_datasets(
    skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db), admin_user: User = Depends(require_admin)
):
    """Admin-only view to list all datasets."""
    service = DatasetService(db, admin_user)
    datasets = await service.list_datasets(skip=skip, limit=limit)

    total_stmt = select(func.count()).select_from(Dataset)
    total = (await db.execute(total_stmt)).scalar() or 0

    dataset_responses = [
        DatasetResponse(
            id=d.id,
            name=d.name,
            description=d.description,
            source_type=d.source_type,
            original_file_name=d.original_file_name,
            file_type=d.file_type,
            uploaded_by=d.uploaded_by,
            upload_status=d.upload_status,
            validation_status=d.validation_status,
            profiling_status=d.profiling_status,
            analysis_status=d.analysis_status,
            record_count=d.record_count,
            column_count=d.column_count,
            active_version_id=d.active_version_id,
            storage_path=d.storage_path,
            metadata=d.metadata_json,
            archived_at=d.archived_at,
            created_at=d.created_at,
            updated_at=d.updated_at,
        )
        for d in datasets
    ]
    return build_success_response(
        data=DatasetListResponse(items=dataset_responses, total=total), message="All datasets retrieved successfully."
    )


@router.get("/reports", response_model=ResponseEnvelope[ReportListResponse])
async def list_admin_reports(
    skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db), admin_user: User = Depends(require_admin)
):
    """Admin-only view to list all reports."""
    repo = ReportService(db, admin_user).repo
    reports = await repo.get_multi(skip=skip, limit=limit)

    total_stmt = select(func.count()).select_from(Report)
    total = (await db.execute(total_stmt)).scalar() or 0

    report_responses = [
        ReportResponse(
            id=r.id,
            dataset_id=r.dataset_id,
            report_type=r.report_type,
            title=r.title,
            generated_by=r.generated_by,
            export_format=r.export_format,
            storage_path=r.storage_path,
            metadata=r.report_metadata_json,
            created_at=r.created_at,
        )
        for r in reports
    ]
    return build_success_response(
        data=ReportListResponse(items=report_responses, total=total), message="All reports retrieved successfully."
    )


@router.get("/audit-logs", response_model=ResponseEnvelope[AuditLogListResponse])
async def list_admin_audit_logs(
    skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db), admin_user: User = Depends(require_admin)
):
    """Admin-only view to query system-wide audit logs."""
    service = SystemAuditLogService(db, admin_user)
    logs = await service.get_all_logs(skip=skip, limit=limit)

    total_stmt = select(func.count()).select_from(AuditLog)
    total = (await db.execute(total_stmt)).scalar() or 0

    log_responses = [
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
        data=AuditLogListResponse(items=log_responses, total=total), message="All audit logs retrieved successfully."
    )


@router.get("/settings", response_model=ResponseEnvelope[List[SystemSettingResponse]])
async def list_settings(db: AsyncSession = Depends(get_db), admin_user: User = Depends(require_admin)):
    """Admin-only view to retrieve all system configuration settings."""
    service = SystemSettingService(db, admin_user)
    settings_list = await service.list_settings()

    responses = [SystemSettingResponse.model_validate(s) for s in settings_list]
    return build_success_response(data=responses, message="System settings retrieved successfully.")


@router.patch("/settings/{setting_key}", response_model=ResponseEnvelope[SystemSettingResponse])
async def update_setting(
    setting_key: str,
    body: SystemSettingUpdateRequest,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    """Admin-only view to modify system settings key-value entries."""
    service = SystemSettingService(db, admin_user)
    setting = await service.update_setting(setting_key, body.setting_value)
    await db.commit()
    return build_success_response(
        data=SystemSettingResponse.model_validate(setting),
        message=f"System setting '{setting_key}' updated successfully.",
    )
