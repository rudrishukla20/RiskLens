import asyncio
from sqlalchemy import select, func
from app.core.database import async_session_maker
from app.models.risk_assessment import RiskAssessment
from app.models.dataset import Dataset

async def run():
    async with async_session_maker() as s:
        ds = (await s.execute(select(Dataset))).scalars().all()
        for d in ds:
            print(f"\nDataset: {d.id} ({d.name})")
            # Query count of risk assessments by category
            res = await s.execute(
                select(RiskAssessment.risk_category, func.count(RiskAssessment.id), func.min(RiskAssessment.risk_score), func.max(RiskAssessment.risk_score))
                .where(RiskAssessment.dataset_id == d.id)
                .group_by(RiskAssessment.risk_category)
            )
            rows = res.all()
            for r in rows:
                print(f"  Category: {r[0]} | Count: {r[1]} | Min Score: {r[2]} | Max Score: {r[3]}")

if __name__ == '__main__':
    asyncio.run(run())
