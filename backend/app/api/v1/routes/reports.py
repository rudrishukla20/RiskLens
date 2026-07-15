import os
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_any_role
from app.core.rate_limit import LIMIT_REPORT, limiter
from app.models.report import Report
from app.models.user import User
from app.responses.envelope import ResponseEnvelope, build_success_response
from app.schemas.report import (
    ReportGenerateRequest,
    ReportListResponse,
    ReportResponse,
)
from app.services.dataset_service import DatasetService
from app.services.report_service import ReportService

router = APIRouter()


@router.post("/generate", response_model=ResponseEnvelope[ReportResponse])
@limiter.limit(LIMIT_REPORT)
async def generate_report(
    request: Request,
    body: ReportGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_any_role),
):
    """
    Triggers generation of an exportable PDF, XLSX, or CSV report document.
    """
    # 1. Resolve version_id if dataset is provided
    version_id = None
    if body.dataset_id:
        dataset_service = DatasetService(db, current_user)
        dataset = await dataset_service.get_dataset(body.dataset_id)
        version_id = dataset.active_version_id
        if not version_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Selected dataset does not have an active version."
            )

    # 2. Resolve document_id if provided in custom parameters
    document_id = None
    if body.custom_parameters:
        doc_id_str = body.custom_parameters.get("document_id")
        if doc_id_str:
            try:
                document_id = uuid.UUID(str(doc_id_str))
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid document_id format in custom_parameters."
                )

    service = ReportService(db, current_user)
    try:
        report = await service.generate_report(
            dataset_id=body.dataset_id,
            version_id=version_id,
            document_id=document_id,
            report_type=body.report_type,
            export_format=body.export_format,
        )
        await db.commit()

        data = ReportResponse(
            id=report.id,
            dataset_id=report.dataset_id,
            report_type=report.report_type,
            title=report.title,
            generated_by=report.generated_by,
            export_format=report.export_format,
            storage_path=report.storage_path,
            metadata=report.report_metadata_json,
            created_at=report.created_at,
        )
        return build_success_response(data=data, message="Report generated successfully.")
    except Exception as e:
        await db.rollback()
        raise e


@router.get("", response_model=ResponseEnvelope[ReportListResponse])
async def list_reports(
    dataset_id: Optional[uuid.UUID] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_any_role),
):
    """
    Lists metadata summaries of compiled reports.
    """
    service = ReportService(db, current_user)

    stmt = select(Report)
    if dataset_id:
        stmt = stmt.where(Report.dataset_id == dataset_id)

    total_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(total_stmt)).scalar() or 0

    stmt = stmt.offset(skip).limit(limit).order_by(Report.created_at.desc())
    res = await db.execute(stmt)
    reports = res.scalars().all()

    responses = [
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
        data=ReportListResponse(items=responses, total=total), message="Reports list retrieved successfully."
    )


@router.get("/{report_id}", response_model=ResponseEnvelope[ReportResponse])
async def get_report(
    report_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_any_role)
):
    """
    Fetches catalog metadata details for a specific report.
    """
    service = ReportService(db, current_user)
    report = await service.repo.get(report_id)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found.")

    data = ReportResponse(
        id=report.id,
        dataset_id=report.dataset_id,
        report_type=report.report_type,
        title=report.title,
        generated_by=report.generated_by,
        export_format=report.export_format,
        storage_path=report.storage_path,
        metadata=report.report_metadata_json,
        created_at=report.created_at,
    )
    return build_success_response(data=data, message="Report details retrieved successfully.")


@router.get("/{report_id}/download")
async def download_report(
    report_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_any_role)
):
    """
    Downloads the physical binary export file (PDF or Excel).
    """
    service = ReportService(db, current_user)
    report = await service.repo.get(report_id)
    if not report or not report.storage_path or not os.path.exists(report.storage_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report file not found on disk.")

    mime_types = {
        "PDF": "application/pdf",
        "XLSX": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "CSV": "text/csv",
    }
    export_format = report.export_format.upper()
    mime_type = mime_types.get(export_format, "application/octet-stream")

    return FileResponse(path=report.storage_path, media_type=mime_type, filename=os.path.basename(report.storage_path))
