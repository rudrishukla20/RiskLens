import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import log_audit_action
from app.core.security import create_access_token, create_refresh_token, verify_password
from app.enums.audit_action import AuditActionEnum
from app.enums.user_status import UserStatusEnum
from app.exceptions.base import AuthenticationException
from app.models.user import User
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository


class AuthService:
    """Service orchestrating JWT authentication and session rotations."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.user_repo = UserRepository(db)
        self.token_repo = RefreshTokenRepository(db)

    async def authenticate_user(
        self, email: str, password: str, ip_address: Optional[str] = None, user_agent: Optional[str] = None
    ) -> User:
        """Verifies credentials, validating status before allowing access."""
        user = await self.user_repo.get_by_email(email)
        if not user or not verify_password(password, user.password_hash):
            # Log failure internally for auditing
            await log_audit_action(
                self.db,
                user_id=user.id if user else None,
                action=AuditActionEnum.FAILED_LOGIN,
                module_name="auth",
                ip_address=ip_address,
                user_agent=user_agent,
                details={"email": email, "reason": "Invalid credentials"},
            )
            raise AuthenticationException(message="Incorrect email or password.")

        if user.status != UserStatusEnum.ACTIVE:
            await log_audit_action(
                self.db,
                user_id=user.id,
                action=AuditActionEnum.FAILED_LOGIN,
                module_name="auth",
                ip_address=ip_address,
                user_agent=user_agent,
                details={"email": email, "reason": "Inactive account"},
            )
            raise AuthenticationException(message="User account is inactive or deactivated.")

        # Update user last login
        user.last_login_at = datetime.now(timezone.utc)
        self.db.add(user)

        await log_audit_action(
            self.db,
            user_id=user.id,
            action=AuditActionEnum.LOGIN,
            module_name="auth",
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return user

    async def create_session(
        self, user: User, ip_address: Optional[str] = None, user_agent: Optional[str] = None
    ) -> Tuple[str, str, int]:
        """Generates new access/refresh tokens and persists the refresh token hash."""
        access_token = create_access_token(subject=user.id)
        refresh_token = create_refresh_token(subject=user.id)

        # Calculate secure hash of refresh token to store in db
        token_hash = hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)

        # Persist refresh token row
        await self.token_repo.create(
            {
                "user_id": user.id,
                "token_hash": token_hash,
                "expires_at": expires_at,
                "created_ip": ip_address,
                "user_agent": user_agent,
            }
        )

        expires_in = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
        return access_token, refresh_token, expires_in

    async def refresh_session(
        self, refresh_token: str, ip_address: Optional[str] = None, user_agent: Optional[str] = None
    ) -> Tuple[str, str, int]:
        """Rotates tokens by checking the signature, expiration, and database validity."""
        try:
            payload = jwt.decode(refresh_token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            user_id_str: Optional[str] = payload.get("sub")
            token_type: Optional[str] = payload.get("type")

            if not user_id_str or token_type != "refresh":
                raise AuthenticationException(message="Invalid refresh token claims.")
        except jwt.PyJWTError:
            raise AuthenticationException(message="Invalid refresh token.")

        token_hash = hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()
        db_token = await self.token_repo.get_by_hash(token_hash)

        if not db_token or db_token.revoked_at or db_token.expires_at.replace(tzinfo=None) < datetime.now(timezone.utc).replace(tzinfo=None):
            raise AuthenticationException(message="Refresh token has been revoked or expired.")

        # Get active user
        user = await self.user_repo.get_with_role(db_token.user_id)
        if not user or user.status != UserStatusEnum.ACTIVE:
            raise AuthenticationException(message="Associated user account is inactive.")

        # Revoke current token (rotation policy)
        await self.token_repo.revoke(db_token)

        # Issue new session
        new_access_token, new_refresh_token, expires_in = await self.create_session(user, ip_address, user_agent)

        await log_audit_action(
            self.db,
            user_id=user.id,
            action=AuditActionEnum.TOKEN_REFRESH,
            module_name="auth",
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return new_access_token, new_refresh_token, expires_in

    async def logout(self, refresh_token: str, user_id: uuid.UUID) -> None:
        """Revokes the active refresh token session."""
        token_hash = hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()
        db_token = await self.token_repo.get_by_hash(token_hash)

        if db_token and db_token.user_id == user_id:
            await self.token_repo.revoke(db_token)
            await log_audit_action(self.db, user_id=user_id, action=AuditActionEnum.LOGOUT, module_name="auth")
