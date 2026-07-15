import asyncio
import uuid
from sqlalchemy import select
from app.core.database import async_session_maker
from app.models.dataset import Dataset
from app.services.analytics.exposure_calculation_service import ExposureCalculationService

async def main():
    async with async_session_maker() as session:
        # Get all datasets
        stmt = select(Dataset).order_by(Dataset.created_at.asc())
        res = await session.execute(stmt)
        datasets = res.scalars().all()
        
        for dataset in datasets:
            print("-" * 50)
            print(f"Checking dataset ID: {dataset.id}, Name: {dataset.name}")
            service = ExposureCalculationService(session)
            total_exp = await service.calculate_total_exposure(dataset.id)
            print(f"Total outstanding exposure calculated: ${total_exp:,.2f}")

            # Dimension breakdown:
            for dim in ["region", "risk_category", "loan_status", "loan_purpose"]:
                breakdown = await service.calculate_exposure_by_dimension(dataset.id, dim)
                print(f"Breakdown by {dim}: {breakdown}")

if __name__ == "__main__":
    asyncio.run(main())
