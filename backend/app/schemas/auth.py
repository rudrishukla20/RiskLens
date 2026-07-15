import uuid

from pydantic import BaseModel, EmailStr, Field

from app.enums.role import RoleEnum
from app.schemas.common import BaseSchema


class LoginRequest(BaseModel):
    """User authentication login request."""

    email: EmailStr = Field(description="User login email address")
    password: str = Field(description="User login password")


class TokenResponse(BaseModel):
    """JWT Access and Refresh token response payload."""

    access_token: str = Field(description="JWT authentication access token")
    refresh_token: str = Field(description="JWT token refresh credential")
    token_type: str = Field(default="bearer", description="Token scheme (typically bearer)")
    expires_in: int = Field(description="Access token validity timeframe in seconds")


class RefreshTokenRequest(BaseModel):
    """Token rotation refresh request."""

    refresh_token: str = Field(description="Valid refresh token string")


class UserMeResponse(BaseSchema):
    """Payload representing currently authenticated user profile."""

    id: uuid.UUID
    email: EmailStr
    full_name: str
    role_code: RoleEnum = Field(serialization_alias="role", description="Active role identifier code")
