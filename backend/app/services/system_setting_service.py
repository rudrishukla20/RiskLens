from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import log_audit_action
from app.enums.audit_action import AuditActionEnum
from app.exceptions.base import NotFoundException
from app.models.system_setting import SystemSetting
from app.models.user import User
from app.repositories.system_setting_repository import SystemSettingRepository


class SystemSettingService:
    """Admin-only service to view and modify system configuration properties."""

    def __init__(self, db: AsyncSession, admin_user: User) -> None:
        self.db = db
        self.admin_user = admin_user
        self.setting_repo = SystemSettingRepository(db)

    async def list_settings(self) -> List[SystemSetting]:
        """Lists all system configuration parameters settings."""
        return await self.setting_repo.get_multi(limit=100)

    async def get_setting(self, key: str) -> SystemSetting:
        """Fetches a specific setting by its unique key identifier."""
        setting = await self.setting_repo.get_by_key(key)
        if not setting:
            raise NotFoundException(message=f"System setting '{key}' not found.")
        return setting

    async def update_setting(self, key: str, value: str) -> SystemSetting:
        """Updates a system setting key-value pair, recording audits trail logs."""
        setting = await self.get_setting(key)

        # Save change
        await self.setting_repo.set_value(key, value, self.admin_user.id)

        await log_audit_action(
            self.db,
            user_id=self.admin_user.id,
            action=AuditActionEnum.SETTINGS_UPDATED,
            module_name="system_settings",
            resource_type="SystemSetting",
            resource_id=key,
            details={"updated_value": value},
        )

        return setting
