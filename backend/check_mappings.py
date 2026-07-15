import asyncio
from sqlalchemy import select
from app.core.database import async_session_maker
from app.models.schema_mapping import SchemaMapping
from app.models.dataset import Dataset

async def run():
    async with async_session_maker() as s:
        ds = (await s.execute(select(Dataset))).scalars().all()
        for d in ds:
            print(f"\nDataset: {d.id} ({d.name})")
            mappings = (await s.execute(select(SchemaMapping).where(SchemaMapping.dataset_id == d.id))).scalars().all()
            for m in mappings:
                print(f"  Canonical: {m.canonical_field} -> Original Column: {m.original_column_name}")

if __name__ == '__main__':
    asyncio.run(run())
