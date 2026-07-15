import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.enums.user_status import UserStatusEnum
from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository managing user account CRUD and status tracking."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(User, db)

    async def get_by_email(self, email: str) -> Optional[User]:
        """Fetches a user account record by email, pre-loading role relationships."""
        stmt = select(self.model).where(self.model.email == email).options(selectinload(self.model.role))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_with_role(self, id: uuid.UUID) -> Optional[User]:
        """Fetches a user account record by ID, pre-loading role relationships."""
        stmt = select(self.model).where(self.model.id == id).options(selectinload(self.model.role))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_users(self, *, skip: int = 0, limit: int = 100) -> List[User]:
        """Lists users with role records pre-loaded."""
        stmt = select(self.model).options(selectinload(self.model.role)).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def deactivate(self, user: User) -> User:
        """Helper to mark a user status deactivated, storing audit timestamp."""
        user.status = UserStatusEnum.DEACTIVATED
        user.deactivated_at = datetime.now(timezone.utc)
        self.db.add(user)
        await self.db.flush()
        return user
