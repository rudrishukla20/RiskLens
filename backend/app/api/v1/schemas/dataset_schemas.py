import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class DatasetFileResponse(BaseModel):
    id: uuid.UUID
    dataset_id: uuid.UUID
    version_id: Optional[uuid.UUID] = None
    original_file_name: str
    stored_file_name: str
    file_extension: str
    file_size_bytes: int
    storage_path: str
    created_at: datetime

    class Config:
        from_attributes = True
        populate_by_name = True
