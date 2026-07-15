import asyncio
from sqlalchemy import select, func
from app.core.database import async_session_maker
from app.models.dataset import Dataset
from app.models.loan import Loan

async def run():
    async with async_session_maker() as s:
        ds = (await s.execute(select(Dataset))).scalars().all()
        print("Datasets:")
        for d in ds:
            # Query loan count for this dataset
            l_cnt = (await s.execute(select(func.count(Loan.id)).where(Loan.dataset_id == d.id))).scalar()
            print(f"ID: {d.id} | Name: {d.name} | Original File: {d.original_file_name} | Loans Count: {l_cnt}")

if __name__ == '__main__':
    asyncio.run(run())
