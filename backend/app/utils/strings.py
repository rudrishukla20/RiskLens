import re
import unicodedata


def clean_string(val: str) -> str:
    """Strips leading/trailing white spaces and collapses multi-spaces."""
    if not val:
        return ""
    return " ".join(val.strip().split())


def normalize_to_ascii(val: str) -> str:
    """Normalizes accented Unicode characters into ASCII representation equivalents."""
    normalized = unicodedata.normalize("NFKD", val)
    return "".join(c for c in normalized if not unicodedata.combining(c))


def slugify(val: str, separator: str = "_") -> str:
    """
    Converts string to a normalized alphanumeric identifier slug.
    Replaces whitespaces and special characters with separators.
    """
    # Normalize unicode to ASCII first
    val = normalize_to_ascii(val)
    val = val.lower()

    # Replace non-alphanumeric chars with separator
    val = re.sub(r"[^a-z0-9]+", separator, val)

    # Clean redundant consecutive separators
    val = re.sub(rf"{separator}+", separator, val)

    return val.strip(separator)


def normalize_column_name(header: str) -> str:
    """
    Normalizes a dataset header column name.
    Used during schema inference to map headers to canonical keys.
    e.g. "Borrower - Annual Income ($)" -> "borrower_annual_income"
    """
    clean_hdr = clean_string(header)
    # Remove unit details like ($), (yrs), %, etc.
    clean_hdr = re.sub(r"\s*\(.*?\)\s*", "", clean_hdr)
    clean_hdr = re.sub(r"\s*\[.*?\]\s*", "", clean_hdr)
    clean_hdr = re.sub(r"\s*\{.*?\}\s*", "", clean_hdr)
    clean_hdr = clean_hdr.replace("%", "percent")

    return slugify(clean_hdr, separator="_")
