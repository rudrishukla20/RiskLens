from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.refresh_token import RefreshToken
from app.repositories.base import BaseRepository


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    """Repository managing secure JWT rotation refresh tokens storage."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(RefreshToken, db)

    async def get_by_hash(self, token_hash: str) -> Optional[RefreshToken]:
        """Queries a refresh token by its SHA256 signature hash."""
        stmt = select(self.model).where(self.model.token_hash == token_hash)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def revoke(self, token: RefreshToken) -> RefreshToken:
        """Revokes a refresh token, storing the revocation timestamp."""
        token.revoked_at = datetime.now(timezone.utc)
        self.db.add(token)
        await self.db.flush()
        return token
