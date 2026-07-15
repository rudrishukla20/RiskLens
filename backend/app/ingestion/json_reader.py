"""
JSON reader — loads a JSON file into a pandas DataFrame.

Supports array-of-objects and records orientation.
"""

import io
import json
import logging
from pathlib import Path
from typing import List, Tuple, Union

import pandas as pd

from app.exceptions.base import DatasetException

logger = logging.getLogger(__name__)


def read_json(
    source: Union[str, Path, io.BytesIO],
    *,
    max_rows: int | None = None,
) -> Tuple[pd.DataFrame, List[str]]:
    """
    Read a JSON file and return ``(DataFrame, original_columns)``.

    Supports:
    - Array of objects: ``[{"col1": v, "col2": v}, ...]``
    - Newline-delimited JSON (one object per line)

    Parameters
    ----------
    source : str | Path | BytesIO
        File path or in-memory byte stream.
    max_rows : int | None
        Optional cap on number of rows.

    Returns
    -------
    tuple[pd.DataFrame, list[str]]

    Raises
    ------
    DatasetException
        If the file cannot be parsed.
    """
    try:
        if isinstance(source, io.BytesIO):
            source.seek(0)
            raw = source.read()
        else:
            with open(source, "rb") as fh:
                raw = fh.read()

        text = raw.decode("utf-8")
        text_stripped = text.strip()

        # Detect format
        if text_stripped.startswith("["):
            # Standard JSON array
            data = json.loads(text_stripped)
            if not isinstance(data, list):
                raise DatasetException(message="JSON root is not an array of objects.")
            df = pd.DataFrame(data)
        elif text_stripped.startswith("{"):
            # Could be single object or newline-delimited
            lines = [ln.strip() for ln in text_stripped.splitlines() if ln.strip()]
            if len(lines) == 1:
                # Single object — wrap as one-row DataFrame
                obj = json.loads(lines[0])
                df = pd.DataFrame([obj])
            else:
                # Newline-delimited JSON
                records = []
                for line in lines:
                    records.append(json.loads(line))
                df = pd.DataFrame(records)
        else:
            raise DatasetException(message="JSON file does not start with '[' or '{'. Unsupported format.")

        if df.empty and df.columns.size == 0:
            raise DatasetException(message="JSON file parsed but produced an empty dataset.")

        if max_rows is not None:
            df = df.head(max_rows)

        original_columns = [str(c) for c in df.columns.tolist()]
        logger.info(
            "JSON parsed successfully: %d rows × %d columns",
            len(df),
            len(original_columns),
        )
        return df, original_columns

    except DatasetException:
        raise
    except json.JSONDecodeError as exc:
        raise DatasetException(message=f"Invalid JSON syntax: {exc}") from exc
    except Exception as exc:
        raise DatasetException(message=f"Failed to parse JSON file: {exc}") from exc
