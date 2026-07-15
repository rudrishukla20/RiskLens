import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.document_analysis_result import DocumentAnalysisResult
from app.models.document_extraction import DocumentExtraction
from app.repositories.base import BaseRepository


class DocumentRepository(BaseRepository[Document]):
    """Repository managing compliance document files database mappings."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Document, db)

    # ── Extractions ───────────────────────────────────────────────────────────
    async def get_extraction(self, document_id: uuid.UUID) -> Optional[DocumentExtraction]:
        """Queries raw OCR parsing results extracted from a document."""
        stmt = select(DocumentExtraction).where(DocumentExtraction.document_id == document_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_extraction(self, extraction: DocumentExtraction) -> DocumentExtraction:
        """Saves OCR parsing extractions outputs."""
        self.db.add(extraction)
        await self.db.flush()
        return extraction

    # ── Analysis Results ──────────────────────────────────────────────────────
    async def get_analysis_result(self, document_id: uuid.UUID) -> Optional[DocumentAnalysisResult]:
        """Queries structured key findings extracted from a document."""
        stmt = select(DocumentAnalysisResult).where(DocumentAnalysisResult.document_id == document_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_analysis_result(self, result_obj: DocumentAnalysisResult) -> DocumentAnalysisResult:
        """Saves compliance structured findings outputs."""
        self.db.add(result_obj)
        await self.db.flush()
        return result_obj
