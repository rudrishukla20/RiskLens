"""Ingestion pipeline — dataset file reading, schema inference, mapping, and canonical transformation."""

from app.ingestion.canonical_transformer import transform_and_populate
from app.ingestion.csv_reader import read_csv
from app.ingestion.excel_reader import read_excel
from app.ingestion.file_validator import validate_upload
from app.ingestion.json_reader import read_json
from app.ingestion.schema_inferer import InferredColumn, infer_schema
from app.ingestion.schema_mapper import persist_confirmed_mappings, persist_inferred_columns

__all__ = [
    "validate_upload",
    "read_csv",
    "read_excel",
    "read_json",
    "InferredColumn",
    "infer_schema",
    "persist_confirmed_mappings",
    "persist_inferred_columns",
    "transform_and_populate",
]
