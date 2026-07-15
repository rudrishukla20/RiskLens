from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import log_audit_action
from app.enums.audit_action import AuditActionEnum
from app.enums.role import RoleEnum
from app.exceptions.base import AuthorizationException
from app.models.audit_log import AuditLog
from app.models.user import User
from app.repositories.audit_log_repository import AuditLogRepository


class AuditLogService:
    """Service to record and query user transaction audit trails logs."""

    def __init__(self, db: AsyncSession, user: User) -> None:
        self.db = db
        self.user = user
        self.audit_repo = AuditLogRepository(db)

    async def log_event(
        self,
        action: AuditActionEnum,
        module_name: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """Records an audit trail event directly to the database."""
        return await log_audit_action(
            self.db,
            user_id=self.user.id,
            action=action,
            module_name=module_name,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details,
        )

    async def get_my_activity(self, *, skip: int = 0, limit: int = 100) -> List[AuditLog]:
        """Queries the personal operations logs feed for the active user."""
        return await self.audit_repo.get_by_user(self.user.id, skip=skip, limit=limit)

    async def get_system_audit_logs(self, *, skip: int = 0, limit: int = 100) -> List[AuditLog]:
        """
        Queries system-wide operational logs.
        Enforced strictly for Admin accounts only.
        """
        if not self.user.role or self.user.role.code != RoleEnum.ADMIN:
            raise AuthorizationException(message="Access denied. Only administrators can view system logs.")

        return await self.audit_repo.get_multi(skip=skip, limit=limit)


class SystemAuditLogService:
    """Read-only system audit log service for admins."""

    def __init__(self, db: AsyncSession, admin_user: User) -> None:
        self.db = db
        self.admin_user = admin_user
        self.audit_repo = AuditLogRepository(db)

        # Enforce role checks
        if not admin_user.role or admin_user.role.code != RoleEnum.ADMIN:
            raise AuthorizationException(message="Access denied. Only administrators can access system logs.")

    async def get_all_logs(self, *, skip: int = 0, limit: int = 100) -> List[AuditLog]:
        return await self.audit_repo.get_multi(skip=skip, limit=limit)
