"""
PDF text extractor — extracts text from PDF files using PyMuPDF (fitz)
with pdfplumber as fallback.

Returns a clean "unavailable for scanned PDFs" message when no text
layer is detected.
"""

import io
import logging
from pathlib import Path
from typing import Union

from app.exceptions.base import DocumentProcessingException

logger = logging.getLogger(__name__)

_MIN_CHARS_PER_PAGE = 20  # pages with fewer chars are considered image-only


def extract_text_from_pdf(
    source: Union[str, Path, bytes],
) -> str:
    """
    Extract all text from a PDF file.

    Uses PyMuPDF (``fitz``) as the primary extractor. If the text yield
    is below threshold, falls back to ``pdfplumber``. If both produce
    negligible text the PDF is assumed to be scanned (image-only).

    Parameters
    ----------
    source : str | Path | bytes
        File path or raw byte content.

    Returns
    -------
    str
        Extracted text content.

    Raises
    ------
    DocumentProcessingException
        If the PDF is scanned with no extractable text layer.
    """
    text_pages = _try_pymupdf(source)

    if text_pages is None:
        text_pages = _try_pdfplumber(source)

    if text_pages is None:
        raise DocumentProcessingException(
            message=(
                "Text extraction is unavailable for scanned PDFs in this version. "
                "Please upload a PDF with an embedded text layer."
            )
        )

    full_text = "\n\n".join(text_pages)
    logger.info("PDF text extraction complete: %d characters across %d pages", len(full_text), len(text_pages))
    return full_text


def _try_pymupdf(source: Union[str, Path, bytes]) -> list[str] | None:
    """Attempt extraction with PyMuPDF (fitz). Returns page texts or None."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        logger.warning("PyMuPDF (fitz) is not installed; skipping primary extractor.")
        return None

    try:
        if isinstance(source, bytes):
            doc = fitz.open(stream=source, filetype="pdf")
        else:
            doc = fitz.open(str(source))

        pages: list[str] = []
        has_text = False

        for page in doc:
            page_text = page.get_text("text") or ""
            pages.append(page_text)
            if len(page_text.strip()) >= _MIN_CHARS_PER_PAGE:
                has_text = True

        doc.close()

        if not has_text:
            return None

        return pages

    except Exception as exc:
        logger.warning("PyMuPDF extraction failed: %s", exc)
        return None


def _try_pdfplumber(source: Union[str, Path, bytes]) -> list[str] | None:
    """Attempt extraction with pdfplumber as fallback. Returns page texts or None."""
    try:
        import pdfplumber
    except ImportError:
        logger.warning("pdfplumber is not installed; skipping fallback extractor.")
        return None

    try:
        if isinstance(source, bytes):
            pdf = pdfplumber.open(io.BytesIO(source))
        else:
            pdf = pdfplumber.open(str(source))

        pages: list[str] = []
        has_text = False

        for page in pdf.pages:
            page_text = page.extract_text() or ""
            pages.append(page_text)
            if len(page_text.strip()) >= _MIN_CHARS_PER_PAGE:
                has_text = True

        pdf.close()

        if not has_text:
            return None

        return pages

    except Exception as exc:
        logger.warning("pdfplumber extraction failed: %s", exc)
        return None
