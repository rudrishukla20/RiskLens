import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.system_setting import SystemSetting
from app.repositories.base import BaseRepository


class SystemSettingRepository(BaseRepository[SystemSetting]):
    """Repository handling key-value system parameters storage updates."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(SystemSetting, db)

    async def get_by_key(self, key: str) -> Optional[SystemSetting]:
        """Queries a setting value object by its unique key."""
        stmt = select(self.model).where(self.model.setting_key == key)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def set_value(
        self, key: str, value: str, updated_by_id: Optional[uuid.UUID] = None
    ) -> Optional[SystemSetting]:
        """Upserts a setting key-value pair, updating the timestamp and user references."""
        setting = await self.get_by_key(key)
        if setting:
            setting.setting_value = value
            if updated_by_id:
                setting.updated_by = updated_by_id
            self.db.add(setting)
            await self.db.flush()
        return setting
