import asyncio
import uuid
from sqlalchemy import select
from app.core.database import async_session_maker
from app.models.raw_record import RawRecord

async def run():
    async with async_session_maker() as s:
        target_id = uuid.UUID('5f0b5f59-6999-44d7-a1c5-25b9d028bb6b')
        res = await s.execute(select(RawRecord).where(RawRecord.dataset_id == target_id).limit(10))
        records = res.scalars().all()
        for idx, r in enumerate(records):
            print(f"Row {idx} raw interest_rate: {r.raw_data_json.get('interest_rate')}")

if __name__ == '__main__':
    asyncio.run(run())
