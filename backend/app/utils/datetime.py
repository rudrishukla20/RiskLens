from datetime import datetime, timezone
from typing import Optional


def get_utc_now() -> datetime:
    """Returns the current timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


def format_iso(dt: datetime) -> str:
    """Formats a datetime into a standardized ISO 8601 string representation."""
    # Ensure dt has tzinfo; if naive, localize to UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def parse_iso(iso_str: str) -> Optional[datetime]:
    """Parses an ISO 8601 string back to a timezone-aware UTC datetime."""
    try:
        dt = datetime.fromisoformat(iso_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (ValueError, TypeError):
        return None
