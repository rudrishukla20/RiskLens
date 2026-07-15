"""
CSV reader — loads a CSV file into a pandas DataFrame.

Handles encoding detection and returns the DataFrame alongside
the original column header list.
"""

import io
import logging
from pathlib import Path
from typing import List, Tuple, Union

import pandas as pd

from app.exceptions.base import DatasetException

logger = logging.getLogger(__name__)

# Encodings to attempt in priority order
_ENCODINGS = ["utf-8", "utf-8-sig", "latin-1", "iso-8859-1", "cp1252"]


def read_csv(
    source: Union[str, Path, io.BytesIO],
    *,
    max_rows: int | None = None,
) -> Tuple[pd.DataFrame, List[str]]:
    """
    Read a CSV file and return ``(DataFrame, original_columns)``.

    Parameters
    ----------
    source : str | Path | BytesIO
        File path or in-memory byte stream.
    max_rows : int | None
        Optional cap on number of rows to read (useful for preview).

    Returns
    -------
    tuple[pd.DataFrame, list[str]]

    Raises
    ------
    DatasetException
        If the file cannot be parsed with any attempted encoding.
    """
    last_err: Exception | None = None

    for enc in _ENCODINGS:
        try:
            # Reset stream position for BytesIO on retries
            if isinstance(source, io.BytesIO):
                source.seek(0)

            df = pd.read_csv(
                source,
                encoding=enc,
                nrows=max_rows,
                on_bad_lines="warn",
                low_memory=False,
            )

            if df.empty and df.columns.size == 0:
                raise DatasetException(message="CSV file appears to be empty or has no headers.")

            original_columns = [str(c) for c in df.columns.tolist()]
            logger.info(
                "CSV parsed successfully (%s encoding): %d rows × %d columns",
                enc,
                len(df),
                len(original_columns),
            )
            return df, original_columns

        except (UnicodeDecodeError, UnicodeError) as exc:
            last_err = exc
            continue
        except DatasetException:
            raise
        except Exception as exc:
            raise DatasetException(message=f"Failed to parse CSV file: {exc}") from exc

    raise DatasetException(
        message=(
            "Could not decode CSV with any supported encoding " f"({', '.join(_ENCODINGS)}). Last error: {last_err}"
        )
    )
