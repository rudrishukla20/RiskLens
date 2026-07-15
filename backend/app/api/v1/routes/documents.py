import os
import shutil
import tempfile
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_any_role
from app.core.rate_limit import LIMIT_AI, LIMIT_UPLOAD, limiter
from app.models.document import Document
from app.models.user import User
from app.repositories.document_repository import DocumentRepository
from app.responses.envelope import ResponseEnvelope, build_success_response
from app.schemas.document import (
    DocumentAnalysisResultResponse,
    DocumentAnalyzeRequest,
    DocumentExtractionResponse,
    DocumentListResponse,
    DocumentResponse,
    DocumentUploadResponse,
)
from app.services.document_service import DocumentService

router = APIRouter()


@router.post("/upload", response_model=ResponseEnvelope[DocumentUploadResponse], status_code=status.HTTP_201_CREATED)
@limiter.limit(LIMIT_UPLOAD)
async def upload_document(
    request: Request,
    dataset_id: Optional[uuid.UUID] = Form(None),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_any_role),
):
    """
    Uploads a compliance document, saves it securely, and logs metadata.
    """
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        shutil.copyfileobj(file.file, tmp)
        temp_path = tmp.name

    file_size = os.path.getsize(temp_path)

    try:
        service = DocumentService(db, current_user)
        document = await service.upload_document(
            original_filename=file.filename, file_size_bytes=file_size, temp_file_path=temp_path, dataset_id=dataset_id
        )
        await db.commit()

        data = DocumentUploadResponse(
            id=document.id,
            dataset_id=document.dataset_id,
            original_file_name=document.original_file_name,
            document_type=document.document_type,
            uploaded_by=document.uploaded_by,
            upload_status=document.upload_status,
            created_at=document.created_at,
        )
        return build_success_response(data=data, message="Document uploaded successfully.")
    except Exception as e:
        await db.rollback()
        raise e
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


@router.get("", response_model=ResponseEnvelope[DocumentListResponse])
async def list_documents(
    skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_any_role)
):
    """
    Lists metadata logs of uploaded documents.
    """
    service = DocumentService(db, current_user)
    documents = await service.list_documents(skip=skip, limit=limit)

    total_stmt = select(func.count()).select_from(Document)
    total = (await db.execute(total_stmt)).scalar() or 0

    responses = [
        DocumentResponse(
            id=d.id,
            dataset_id=d.dataset_id,
            original_file_name=d.original_file_name,
            document_type=d.document_type,
            uploaded_by=d.uploaded_by,
            upload_status=d.upload_status,
            analysis_status=d.analysis_status,
            storage_path=d.storage_path,
            file_size_bytes=d.file_size_bytes,
            checksum_sha256=d.checksum_sha256,
            created_at=d.created_at,
        )
        for d in documents
    ]
    return build_success_response(
        data=DocumentListResponse(items=responses, total=total), message="Documents list retrieved successfully."
    )


@router.get("/{document_id}", response_model=ResponseEnvelope[DocumentResponse])
async def get_document(
    document_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_any_role)
):
    """
    Fetches compliance document upload status and lifecycle metadata.
    """
    service = DocumentService(db, current_user)
    d = await service.get_document(document_id)

    data = DocumentResponse(
        id=d.id,
        dataset_id=d.dataset_id,
        original_file_name=d.original_file_name,
        document_type=d.document_type,
        uploaded_by=d.uploaded_by,
        upload_status=d.upload_status,
        analysis_status=d.analysis_status,
        storage_path=d.storage_path,
        file_size_bytes=d.file_size_bytes,
        checksum_sha256=d.checksum_sha256,
        created_at=d.created_at,
    )
    return build_success_response(data=data, message="Document details retrieved successfully.")


@router.post("/{document_id}/analyze", response_model=ResponseEnvelope[DocumentAnalysisResultResponse])
@limiter.limit(LIMIT_AI)
async def analyze_document(
    request: Request,
    document_id: uuid.UUID,
    body: DocumentAnalyzeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_any_role),
):
    """
    Runs financial analysis rules on a document.
    """
    service = DocumentService(db, current_user)
    try:
        result = await service.analyze_document(document_id)
        await db.commit()

        data = DocumentAnalysisResultResponse(
            id=result.id,
            document_id=result.document_id,
            executive_summary=result.executive_summary,
            key_findings=result.key_findings_json,
            risk_notes=result.risk_notes_json,
            compliance_observations=result.compliance_observations_json,
            extracted_financial_ratios=result.extracted_financial_ratios_json,
            created_at=result.created_at,
        )
        return build_success_response(data=data, message="Document analysis triggered and completed successfully.")
    except Exception as e:
        await db.rollback()
        raise e


@router.get("/{document_id}/analysis", response_model=ResponseEnvelope[DocumentAnalysisResultResponse])
async def get_document_analysis(
    document_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_any_role)
):
    """
    Fetches the structured analysis result for a document.
    """
    service = DocumentService(db, current_user)
    # Ensure document exists
    await service.get_document(document_id)

    repo = DocumentRepository(db)
    result = await repo.get_analysis_result(document_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document analysis results not found for this document."
        )

    data = DocumentAnalysisResultResponse(
        id=result.id,
        document_id=result.document_id,
        executive_summary=result.executive_summary,
        key_findings=result.key_findings_json,
        risk_notes=result.risk_notes_json,
        compliance_observations=result.compliance_observations_json,
        extracted_financial_ratios=result.extracted_financial_ratios_json,
        created_at=result.created_at,
    )
    return build_success_response(data=data, message="Document analysis results retrieved successfully.")


@router.get("/{document_id}/extraction", response_model=ResponseEnvelope[DocumentExtractionResponse])
async def get_document_extraction(
    document_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_any_role)
):
    """
    Fetches the raw text and tabular extraction logs for a compliance document.
    """
    service = DocumentService(db, current_user)
    await service.get_document(document_id)

    repo = DocumentRepository(db)
    ext = await repo.get_extraction(document_id)
    if not ext:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document extraction logs not found. Process document first."
        )

    data = DocumentExtractionResponse(
        id=ext.id,
        document_id=ext.document_id,
        extracted_text=ext.extracted_text,
        extracted_tables=ext.extracted_tables_json,
        metadata=ext.metadata_json,
        page_count=ext.page_count,
        extraction_status=ext.extraction_status,
        created_at=ext.created_at,
    )
    return build_success_response(data=data, message="Document extraction results retrieved successfully.")
