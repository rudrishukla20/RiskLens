from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums.role import RoleEnum
from app.models.role import Role
from app.repositories.base import BaseRepository


class RoleRepository(BaseRepository[Role]):
    """Repository handling read-only queries for user security roles."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Role, db)

    async def get_by_code(self, code: RoleEnum) -> Optional[Role]:
        """Queries a role metadata record by its unique code identifier."""
        stmt = select(self.model).where(self.model.code == code)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
