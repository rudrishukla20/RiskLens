import decimal
import json
import uuid
from datetime import date, datetime
from enum import Enum
from typing import Any


class CustomJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder to support UUID, datetime, date, Decimal, and Enum instances serialization."""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, uuid.UUID):
            return str(obj)
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, decimal.Decimal):
            return float(obj)
        if isinstance(obj, Enum):
            return obj.value
        return super().default(obj)


def json_encode(data: Any) -> str:
    """Safely serializes a Python object to a JSON formatted string."""
    return json.dumps(data, cls=CustomJSONEncoder)


def json_decode(json_str: str) -> Any:
    """Safely deserializes a JSON formatted string back to a Python object."""
    if not json_str:
        return None
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        return None
