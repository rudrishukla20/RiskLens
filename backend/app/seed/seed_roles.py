import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums.role import RoleEnum
from app.models.role import Role


async def seed_roles(db: AsyncSession) -> None:
    """Idempotently seeds platform security roles."""
    roles_data = [
        {
            "code": RoleEnum.ADMIN,
            "name": "System Administrator",
            "description": "Full access to platform administration, system settings, and user auditing.",
        },
        {
            "code": RoleEnum.CREDIT_RISK_GOVERNANCE_OFFICER,
            "name": "Credit Risk Governance Officer",
            "description": "Full access to credit risk analytics, data validation, profiling, AI insights, and reporting.",
        },
    ]

    for rdata in roles_data:
        # Check if the role already exists by its unique code
        stmt = select(Role).where(Role.code == rdata["code"])
        result = await db.execute(stmt)
        existing_role = result.scalar_one_or_none()

        if not existing_role:
            role = Role(
                id=uuid.uuid4(),
                code=rdata["code"],
                name=rdata["name"],
                description=rdata["description"],
                is_active=True,
            )
            db.add(role)
            print(f"Role seeded: {rdata['code']}")
        else:
            # Sync name and description if they changed
            existing_role.name = rdata["name"]
            existing_role.description = rdata["description"]
            print(f"Role verified: {rdata['code']}")

    await db.flush()
