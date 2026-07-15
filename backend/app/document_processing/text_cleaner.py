"""
Text cleaner — normalises extracted document text.

Collapses whitespace, strips control characters, normalises unicode,
and removes common page header/footer patterns.
"""

import re
import unicodedata
from typing import Optional


def clean_extracted_text(text: str) -> str:
    """
    Apply a full normalisation pipeline to raw extracted text.

    Steps
    -----
    1. Normalise Unicode (NFC form).
    2. Remove control characters (except newlines and tabs).
    3. Remove page number patterns (e.g. ``"Page 3 of 10"``, ``"- 3 -"``).
    4. Collapse multiple blank lines to a single separator.
    5. Collapse multiple spaces to single space per line.
    6. Strip leading/trailing whitespace.

    Parameters
    ----------
    text : str
        Raw text from PDF or DOCX extraction.

    Returns
    -------
    str
        Cleaned text.
    """
    if not text:
        return ""

    # 1. Unicode normalisation
    text = unicodedata.normalize("NFC", text)

    # 2. Remove control chars except \n, \r, \t
    text = re.sub(r"[^\S \n\r\t]", "", text)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

    # 3. Remove common page number patterns
    text = re.sub(r"(?im)^\s*page\s+\d+\s*(of\s+\d+)?\s*$", "", text)
    text = re.sub(r"(?m)^\s*-\s*\d+\s*-\s*$", "", text)
    text = re.sub(r"(?m)^\s*\d+\s*$", "", text)  # lone page numbers on their own line

    # 4. Collapse multiple blank lines into two newlines
    text = re.sub(r"\n{3,}", "\n\n", text)

    # 5. Collapse multiple spaces within each line
    lines = text.split("\n")
    cleaned_lines = []
    for line in lines:
        cleaned_lines.append(" ".join(line.split()))
    text = "\n".join(cleaned_lines)

    # 6. Strip
    text = text.strip()

    return text


def truncate_text(text: str, max_length: int = 50_000) -> str:
    """
    Truncate text to a maximum character length, appending an indicator
    if truncation occurred.
    """
    if len(text) <= max_length:
        return text
    return text[:max_length] + "\n\n[… text truncated at {:,} characters]".format(max_length)


def extract_sections(
    text: str,
    heading_pattern: Optional[str] = None,
) -> dict[str, str]:
    """
    Split text into sections based on a heading regex pattern.

    Parameters
    ----------
    heading_pattern : str | None
        Regex capturing the heading text. Defaults to all-caps lines
        of 3+ characters as section headers.

    Returns
    -------
    dict[str, str]
        ``{section_heading: section_body}``
    """
    if heading_pattern is None:
        heading_pattern = r"^([A-Z][A-Z\s]{2,})$"

    sections: dict[str, str] = {}
    current_heading = "PREAMBLE"
    current_body: list[str] = []

    for line in text.split("\n"):
        match = re.match(heading_pattern, line.strip(), re.MULTILINE)
        if match:
            # Save previous section
            if current_body:
                sections[current_heading] = "\n".join(current_body).strip()
            current_heading = match.group(1).strip()
            current_body = []
        else:
            current_body.append(line)

    # Save last section
    if current_body:
        sections[current_heading] = "\n".join(current_body).strip()

    return sections
