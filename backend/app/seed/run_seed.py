import asyncio
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_maker
from app.models.system_setting import SystemSetting
from app.seed.seed_admin import seed_admin
from app.seed.seed_public_dataset_sources import seed_public_dataset_sources
from app.seed.seed_roles import seed_roles


async def seed_system_settings(db: AsyncSession) -> None:
    """Idempotently seeds standard system setting keys."""
    settings_data = [
        {
            "key": "max_upload_size_mb",
            "value": "50",
            "type": "INTEGER",
            "description": "Maximum file size limit allowed for uploads in Megabytes.",
        },
        {
            "key": "allowed_structured_extensions",
            "value": ".csv,.xlsx,.json",
            "type": "STRING",
            "description": "Comma-separated list of allowed structured dataset file extensions.",
        },
        {
            "key": "allowed_document_extensions",
            "value": ".pdf,.docx",
            "type": "STRING",
            "description": "Comma-separated list of allowed compliance document file extensions.",
        },
        {
            "key": "password_min_length",
            "value": "12",
            "type": "INTEGER",
            "description": "Minimum length required for user passwords.",
        },
        {
            "key": "ai_provider",
            "value": "disabled",
            "type": "STRING",
            "description": "Active AI commentary provider. Options: disabled, openai, anthropic.",
        },
    ]

    for sdata in settings_data:
        stmt = select(SystemSetting).where(SystemSetting.setting_key == sdata["key"])
        res = await db.execute(stmt)
        existing_setting = res.scalar_one_or_none()

        if not existing_setting:
            setting = SystemSetting(
                id=uuid.uuid4(),
                setting_key=sdata["key"],
                setting_value=sdata["value"],
                setting_type=sdata["type"],
                description=sdata["description"],
            )
            db.add(setting)
            print(f"System setting seeded: {sdata['key']}")
        else:
            # Sync value and description if changed
            existing_setting.description = sdata["description"]
            print(f"System setting verified: {sdata['key']}")

    await db.flush()


async def run_all_seeds() -> None:
    """Orchestrator running all seed scripts sequentially within a database transaction transaction."""
    print("Starting database seeding process...")
    async with async_session_maker() as db:
        try:
            # 1. Seed Roles (dependencies for Users)
            await seed_roles(db)

            # 2. Seed Admin User
            await seed_admin(db)

            # 3. Seed Public dataset catalog references
            await seed_public_dataset_sources(db)

            # 4. Seed system configurations
            await seed_system_settings(db)

            # Commit all operations
            await db.commit()
            print("Database seeding completed successfully.")
        except Exception as e:
            await db.rollback()
            print(f"Database seeding failed and transaction rolled back: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(run_all_seeds())
