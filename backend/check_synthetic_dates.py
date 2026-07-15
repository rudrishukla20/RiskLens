import asyncio
import uuid
from sqlalchemy import select
from app.core.database import async_session_maker
from app.models.loan import Loan

async def run():
    async with async_session_maker() as s:
        target_id = uuid.UUID('5f0b5f59-6999-44d7-a1c5-25b9d028bb6b')
        res = await s.execute(select(Loan).where(Loan.dataset_id == target_id).limit(5))
        loans = res.scalars().all()
        for idx, l in enumerate(loans):
            print(f"Loan {idx} | Date: {l.disbursement_date} | Addr Attrs: {l.additional_attributes_json}")

if __name__ == '__main__':
    asyncio.run(run())
