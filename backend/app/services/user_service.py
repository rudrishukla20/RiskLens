import uuid
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import log_audit_action
from app.core.security import get_password_hash, validate_password_strength
from app.enums.audit_action import AuditActionEnum
from app.enums.role import RoleEnum
from app.enums.user_status import UserStatusEnum
from app.exceptions.base import ConflictException, NotFoundException, ValidationException
from app.models.user import User
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository


class UserService:
    """Admin-only service to manage user accounts provisioning and roles updates."""

    def __init__(self, db: AsyncSession, admin_user: User) -> None:
        self.db = db
        self.admin_user = admin_user
        self.user_repo = UserRepository(db)
        self.role_repo = RoleRepository(db)

    async def create_user(self, email: str, full_name: str, password: str, role_code: RoleEnum) -> User:
        """Creates a new user account, validating password strength rules and assigned roles."""
        # 1. Enforce Role Assignment Limits (only ADMIN and CREDIT_RISK_GOVERNANCE_OFFICER)
        if role_code not in (RoleEnum.ADMIN, RoleEnum.CREDIT_RISK_GOVERNANCE_OFFICER):
            raise ValidationException(message="Invalid role assignment.")

        # 2. Check password strength
        validate_password_strength(password)

        # 3. Check duplicate email conflicts
        existing_user = await self.user_repo.get_by_email(email)
        if existing_user:
            raise ConflictException(message="A user with this email address already exists.")

        # 4. Resolve role database ID
        role = await self.role_repo.get_by_code(role_code)
        if not role:
            raise NotFoundException(message="Assigned role not found.")

        # 5. Save user
        hashed_password = get_password_hash(password)
        user = await self.user_repo.create(
            {
                "email": email,
                "full_name": full_name,
                "password_hash": hashed_password,
                "role_id": role.id,
                "status": UserStatusEnum.ACTIVE,
                "created_by": self.admin_user.id,
            }
        )

        await log_audit_action(
            self.db,
            user_id=self.admin_user.id,
            action=AuditActionEnum.USER_CREATED,
            module_name="user_mgmt",
            resource_type="User",
            resource_id=str(user.id),
            details={"email": email, "role": role_code},
        )

        # Reload with role loaded
        return await self.user_repo.get_with_role(user.id)

    async def list_users(self, *, skip: int = 0, limit: int = 100) -> List[User]:
        """Lists users accounts."""
        return await self.user_repo.list_users(skip=skip, limit=limit)

    async def get_user(self, user_id: uuid.UUID) -> User:
        """Fetches a specific user profile by ID."""
        user = await self.user_repo.get_with_role(user_id)
        if not user:
            raise NotFoundException(message="User not found.")
        return user

    async def update_user(
        self,
        user_id: uuid.UUID,
        email: Optional[str] = None,
        full_name: Optional[str] = None,
        password: Optional[str] = None,
        role_code: Optional[RoleEnum] = None,
        status: Optional[UserStatusEnum] = None,
    ) -> User:
        """Updates user profile properties, validation limits, and status states."""
        user = await self.get_user(user_id)
        updates = {}

        if email:
            existing_email = await self.user_repo.get_by_email(email)
            if existing_email and existing_email.id != user_id:
                raise ConflictException(message="A user with this email address already exists.")
            updates["email"] = email

        if full_name:
            updates["full_name"] = full_name

        if password:
            validate_password_strength(password)
            updates["password_hash"] = get_password_hash(password)

        if role_code:
            if role_code not in (RoleEnum.ADMIN, RoleEnum.CREDIT_RISK_GOVERNANCE_OFFICER):
                raise ValidationException(message="Invalid role assignment.")
            role = await self.role_repo.get_by_code(role_code)
            if not role:
                raise NotFoundException(message="Role not found.")
            updates["role_id"] = role.id

        if status:
            updates["status"] = status
            if status == UserStatusEnum.DEACTIVATED:
                # Delegate to deactivation to save deactivation timestamp
                await self.user_repo.deactivate(user)
                await log_audit_action(
                    self.db,
                    user_id=self.admin_user.id,
                    action=AuditActionEnum.USER_DEACTIVATED,
                    module_name="user_mgmt",
                    resource_type="User",
                    resource_id=str(user_id),
                )
                return await self.user_repo.get_with_role(user_id)

        # Commit fields updates
        await self.user_repo.update(db_obj=user, obj_in=updates)

        await log_audit_action(
            self.db,
            user_id=self.admin_user.id,
            action=AuditActionEnum.USER_UPDATED,
            module_name="user_mgmt",
            resource_type="User",
            resource_id=str(user_id),
            details={"updated_fields": list(updates.keys())},
        )

        return await self.user_repo.get_with_role(user_id)

    async def deactivate_user(self, user_id: uuid.UUID) -> User:
        """Deactivates a user account (soft delete)."""
        user = await self.get_user(user_id)
        await self.user_repo.deactivate(user)

        await log_audit_action(
            self.db,
            user_id=self.admin_user.id,
            action=AuditActionEnum.USER_DEACTIVATED,
            module_name="user_mgmt",
            resource_type="User",
            resource_id=str(user_id),
        )
        return await self.user_repo.get_with_role(user_id)
