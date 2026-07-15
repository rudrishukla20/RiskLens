import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field

from app.enums.role import RoleEnum
from app.enums.user_status import UserStatusEnum
from app.schemas.common import BaseSchema, TimestampModel, UUIDModel


class UserBase(BaseModel):
    email: EmailStr = Field(description="Unique email address")
    full_name: str = Field(description="First and last name")


class UserCreate(UserBase):
    """User provisioning creation payload."""

    password: str = Field(min_length=12, description="Password meeting minimum security rules")
    role_code: RoleEnum = Field(description="Assigned platform role")


class UserUpdate(BaseModel):
    """User modification update payload."""

    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = Field(default=None, min_length=12, description="Optional new password")
    role_code: Optional[RoleEnum] = None
    status: Optional[UserStatusEnum] = None


class UserResponse(UUIDModel, TimestampModel):
    """User detail data response payload."""

    email: EmailStr
    full_name: str
    status: UserStatusEnum
    role_code: RoleEnum = Field(serialization_alias="role")
    last_login_at: Optional[datetime] = None
    created_by: Optional[uuid.UUID] = None
    deactivated_at: Optional[datetime] = None


class UserListResponse(BaseSchema):
    """List response of users."""

    items: List[UserResponse]
    total: int
