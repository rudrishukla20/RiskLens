import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import get_password_hash
from app.enums.role import RoleEnum
from app.enums.user_status import UserStatusEnum
from app.models.role import Role
from app.models.user import User


async def seed_admin(db: AsyncSession) -> None:
    """Idempotently seeds the default platform administrator user."""
    email = settings.SEED_ADMIN_EMAIL
    full_name = settings.SEED_ADMIN_FULL_NAME
    password = settings.SEED_ADMIN_PASSWORD

    # 1. Fetch ADMIN role id
    stmt_role = select(Role).where(Role.code == RoleEnum.ADMIN)
    res_role = await db.execute(stmt_role)
    admin_role = res_role.scalar_one_or_none()

    if not admin_role:
        print("Skipping admin seed: ADMIN role not found in database. Run seed_roles first.")
        return

    # 2. Check if admin user exists by email
    stmt_user = select(User).where(User.email == email)
    res_user = await db.execute(stmt_user)
    existing_user = res_user.scalar_one_or_none()

    if not existing_user:
        hashed_password = get_password_hash(password)
        admin = User(
            id=uuid.uuid4(),
            role_id=admin_role.id,
            email=email,
            full_name=full_name,
            password_hash=hashed_password,
            status=UserStatusEnum.ACTIVE,
        )
        db.add(admin)
        print(f"Admin user seeded: {email}")
    else:
        # Sync values if needed
        existing_user.full_name = full_name
        existing_user.role_id = admin_role.id
        print(f"Admin user verified: {email}")

    await db.flush()
