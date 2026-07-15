import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import Field

from app.enums.audit_action import AuditActionEnum
from app.schemas.common import BaseSchema, UUIDModel


class AuditLogResponse(UUIDModel):
    """A single detailed transaction audit record."""

    user_id: Optional[uuid.UUID] = None
    request_id: Optional[str] = None
    action: AuditActionEnum
    module_name: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    details_json: Optional[Dict[str, Any]] = Field(default=None, serialization_alias="details")
    created_at: datetime


class AuditLogListResponse(BaseSchema):
    """Activity feed wrapper."""

    items: List[AuditLogResponse]
    total: int
