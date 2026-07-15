from enum import Enum


class FileTypeEnum(str, Enum):
    CSV = "CSV"
    XLSX = "XLSX"
    JSON = "JSON"
    PDF = "PDF"
    DOCX = "DOCX"
