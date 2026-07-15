import asyncio
from sqlalchemy import select, func
from app.core.database import async_session_maker
from app.models.dataset import Dataset
from app.models.dataset_version import DatasetVersion

async def run():
    async with async_session_maker() as s:
        ds = (await s.execute(select(Dataset))).scalars().all()
        for d in ds:
            res = await s.execute(select(func.count(DatasetVersion.id)).where(DatasetVersion.dataset_id == d.id))
            cnt = res.scalar()
            print(f"Dataset: {d.id} ({d.name}) | Version count: {cnt}")
            if cnt > 0:
                vers = (await s.execute(select(DatasetVersion).where(DatasetVersion.dataset_id == d.id).order_by(DatasetVersion.version_number))).scalars().all()
                for v in vers:
                    print(f"  Version: {v.id} | Number: {v.version_number}")

if __name__ == '__main__':
    asyncio.run(run())
