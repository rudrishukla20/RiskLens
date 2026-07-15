import uuid
from typing import Any, Dict, List, Optional

import jwt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import get_db
from app.core.logging import request_id_ctx
from app.enums.audit_action import AuditActionEnum
from app.enums.role import RoleEnum
from app.enums.user_status import UserStatusEnum
from app.exceptions.base import AuthenticationException, AuthorizationException
from app.models.audit_log import AuditLog
from app.models.user import User

# OAuth2 password bearer flow definition
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login", auto_error=False)


async def get_current_user(db: AsyncSession = Depends(get_db), token: Optional[str] = Depends(oauth2_scheme)) -> User:
    """
    FastAPI dependency extracting, decoding, and validating the current user's JWT.
    Enforces active user checks and pre-loads user role codes.
    """
    if not token:
        raise AuthenticationException(message="Not authenticated.")

    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id_str: Optional[str] = payload.get("sub")
        token_type: Optional[str] = payload.get("type")

        if not user_id_str or token_type != "access":
            raise AuthenticationException(message="Invalid token claims.")

        user_id = uuid.UUID(user_id_str)
    except (jwt.PyJWTError, ValueError):
        raise AuthenticationException(message="Could not validate credentials.")

    # Execute query pre-loading the role relationship
    stmt = select(User).where(User.id == user_id).options(selectinload(User.role))
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise AuthenticationException(message="User not found.")

    if user.status != UserStatusEnum.ACTIVE:
        raise AuthenticationException(message="User account is inactive or deactivated.")

    return user


class RoleChecker:
    """Enforceable FastAPI dependency guard validating permissions constraints."""

    def __init__(self, allowed_roles: List[RoleEnum]) -> None:
        self.allowed_roles = [role.value for role in allowed_roles]

    def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        # User role relationship must be pre-loaded
        print(f"DEBUG ROLECHECK: user={current_user.email}, role={current_user.role}, role_code={current_user.role.code if current_user.role else 'None'}, allowed={self.allowed_roles}", flush=True)
        if not current_user.role or current_user.role.code not in self.allowed_roles:
            raise AuthorizationException(message="Access forbidden. Insufficient privileges.")
        return current_user


# Role dependency shortcuts
require_admin = RoleChecker([RoleEnum.ADMIN])
require_governance = RoleChecker([RoleEnum.CREDIT_RISK_GOVERNANCE_OFFICER])
require_any_role = RoleChecker([RoleEnum.ADMIN, RoleEnum.CREDIT_RISK_GOVERNANCE_OFFICER])


async def log_audit_action(
    db: AsyncSession,
    user_id: Optional[uuid.UUID],
    action: AuditActionEnum,
    module_name: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> AuditLog:
    """
    Hook function to persist audit events programmatically.
    Automatically captures the request context tracing ID if available.
    """
    req_id = request_id_ctx.get() or None

    audit_log = AuditLog(
        user_id=user_id,
        request_id=req_id,
        action=action,
        module_name=module_name,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=ip_address,
        user_agent=user_agent,
        details_json=details,
    )
    db.add(audit_log)
    await db.flush()
    return audit_log
