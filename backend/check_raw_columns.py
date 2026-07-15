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
        for l in loans:
            print(f"\nDataset: {l.dataset_id} | Loan ID: {l.id}")
            print(f"  delinquency_days: {l.delinquency_days}")
            print(f"  loan_status: {l.loan_status}")
            print(f"  additional_attributes: {l.additional_attributes_json}")

if __name__ == '__main__':
    asyncio.run(run())
