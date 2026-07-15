import asyncio
from sqlalchemy import select, func
from app.core.database import async_session_maker
from app.models.loan import Loan
from app.models.dataset import Dataset

async def run():
    async with async_session_maker() as s:
        ds = (await s.execute(select(Dataset))).scalars().all()
        for d in ds:
            print(f"\nDataset: {d.id} ({d.name})")
            # Query count, min, max, mean, and count of unique rates
            res = await s.execute(select(
                func.count(Loan.id),
                func.min(Loan.interest_rate),
                func.max(Loan.interest_rate),
                func.avg(Loan.interest_rate),
                func.count(Loan.interest_rate.distinct())
            ).where(Loan.dataset_id == d.id))
            cnt, min_val, max_val, avg_val, unique_cnt = res.first()
            print(f"  Count: {cnt} | Min: {min_val} | Max: {max_val} | Avg: {avg_val} | Unique Rates: {unique_cnt}")
            if unique_cnt < 10:
                res_unique = await s.execute(select(Loan.interest_rate, func.count(Loan.id)).where(Loan.dataset_id == d.id).group_by(Loan.interest_rate))
                for row in res_unique.all():
                    print(f"    {row[0]}: {row[1]}")

if __name__ == '__main__':
    asyncio.run(run())
