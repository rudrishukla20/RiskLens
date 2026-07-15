import asyncio
from sqlalchemy import select, func
from app.core.database import async_session_maker
from app.models.loan import Loan
from app.models.dataset import Dataset

async def run():
    async with async_session_maker() as s:
        ds = (await s.execute(select(Dataset))).scalars().all()
        for d in ds:
            res = await s.execute(
                select(
                    func.count(Loan.id),
                    func.count(Loan.disbursement_date),
                    func.min(Loan.disbursement_date),
                    func.max(Loan.disbursement_date)
                ).where(Loan.dataset_id == d.id)
            )
            total, dates_cnt, min_date, max_date = res.first()
            print(f"Dataset: {d.id} ({d.name}) | Total: {total} | Disbursement Dates: {dates_cnt} | Min: {min_date} | Max: {max_date}")

if __name__ == '__main__':
    asyncio.run(run())
