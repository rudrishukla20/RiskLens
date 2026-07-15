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
            # Unique status
            status_stmt = select(Loan.loan_status, func.count(Loan.id)).where(Loan.dataset_id == d.id).group_by(Loan.loan_status)
            statuses = (await s.execute(status_stmt)).all()
            print("  Unique loan_status:")
            for row in statuses:
                print(f"    {row[0]}: {row[1]}")

            # Unique purpose
            purpose_stmt = select(Loan.loan_purpose, func.count(Loan.id)).where(Loan.dataset_id == d.id).group_by(Loan.loan_purpose)
            purposes = (await s.execute(purpose_stmt)).all()
            print("  Unique loan_purpose:")
            for row in purposes:
                print(f"    {row[0]}: {row[1]}")

if __name__ == '__main__':
    asyncio.run(run())
