import asyncio
from sqlalchemy import select
from app.core.database import async_session_maker
from app.models.raw_record import RawRecord

async def run():
    async with async_session_maker() as s:
        res = await s.execute(select(RawRecord))
        records = res.scalars().all()
        seen = set()
        for r in records:
            if r.dataset_id not in seen:
                seen.add(r.dataset_id)
                print(f"\nDataset: {r.dataset_id}")
                print(f"  Raw Keys: {list(r.raw_data_json.keys())}")
                print("  Raw Row Sample:")
                for k, v in list(r.raw_data_json.items())[:15]:
                    print(f"    {k}: {v}")

if __name__ == '__main__':
    asyncio.run(run())
