"""
Excel reader — loads an XLSX file into a pandas DataFrame.

Uses the openpyxl engine and returns the DataFrame alongside
the original column header list.
"""

import io
import logging
from pathlib import Path
from typing import List, Tuple, Union

import pandas as pd

from app.exceptions.base import DatasetException

logger = logging.getLogger(__name__)


def read_excel(
    source: Union[str, Path, io.BytesIO],
    *,
    sheet_name: Union[str, int] = 0,
    max_rows: int | None = None,
) -> Tuple[pd.DataFrame, List[str]]:
    """
    Read an XLSX file and return ``(DataFrame, original_columns)``.

    Parameters
    ----------
    source : str | Path | BytesIO
        File path or in-memory byte stream.
    sheet_name : str | int
        Sheet name or 0-based index. Defaults to the first sheet.
    max_rows : int | None
        Optional cap on number of rows to read.

    Returns
    -------
    tuple[pd.DataFrame, list[str]]

    Raises
    ------
    DatasetException
        If the file cannot be read or is empty.
    """
    try:
        if isinstance(source, io.BytesIO):
            source.seek(0)

        df = pd.read_excel(
            source,
            sheet_name=sheet_name,
            engine="openpyxl",
            nrows=max_rows,
        )

        if df.empty and df.columns.size == 0:
            raise DatasetException(message="Excel file appears to be empty or has no headers.")

        original_columns = [str(c) for c in df.columns.tolist()]
        logger.info(
            "Excel parsed successfully: %d rows × %d columns",
            len(df),
            len(original_columns),
        )
        return df, original_columns

    except DatasetException:
        raise
    except Exception as exc:
        raise DatasetException(message=f"Failed to parse Excel file: {exc}") from exc
