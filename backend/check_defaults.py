import asyncio
from sqlalchemy import select, func
from app.core.database import async_session_maker
from app.models.loan import Loan
from app.models.dataset import Dataset

async def run():
    async with async_session_maker() as s:
        ds = (await s.execute(select(Dataset))).scalars().all()
        for d in ds:
            cnt_default = (await s.execute(select(func.count(Loan.id)).where(Loan.dataset_id == d.id, Loan.historical_default_flag == True))).scalar()
            cnt_false = (await s.execute(select(func.count(Loan.id)).where(Loan.dataset_id == d.id, Loan.historical_default_flag == False))).scalar()
            cnt_none = (await s.execute(select(func.count(Loan.id)).where(Loan.dataset_id == d.id, Loan.historical_default_flag.is_(None)))).scalar()
            print(f"Dataset: {d.id} ({d.name}) | Default True: {cnt_default} | Default False: {cnt_false} | Default None: {cnt_none}")

if __name__ == '__main__':
    asyncio.run(run())
