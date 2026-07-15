import asyncio
import uuid
from sqlalchemy import select
from app.core.database import async_session_maker
from app.models.loan import Loan

async def run():
    async with async_session_maker() as s:
        target_id = uuid.UUID('5f0b5f59-6999-44d7-a1c5-25b9d028bb6b')
        res = await s.execute(select(Loan).where(Loan.dataset_id == target_id).limit(1))
        loan = res.scalar_one_or_none()
        if loan:
            print("Loan Attributes:")
            for attr in dir(loan):
                if not attr.startswith('_') and attr not in ('metadata', 'registry', 'dataset', 'version', 'borrower'):
                    print(f"  {attr}: {getattr(loan, attr)}")

if __name__ == '__main__':
    asyncio.run(run())
