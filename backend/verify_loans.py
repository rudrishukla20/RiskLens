import asyncio
import uuid
from app.core.database import async_session_maker
from app.services.analytics_service import AnalyticsService
from app.models.dataset import Dataset
from app.models.user import User
from sqlalchemy import select

async def main():
    async with async_session_maker() as session:
        # Get active user
        admin_user = (await session.execute(select(User).where(User.email == "admin@risklens.com"))).scalar_one()

        # Get first dataset
        stmt = select(Dataset).order_by(Dataset.created_at.asc())
        res = await session.execute(stmt)
        datasets = res.scalars().all()

        service = AnalyticsService(session, admin_user)

        for dataset in datasets:
            print("-" * 50)
            print(f"Checking Dataset: {dataset.id} | Name: {dataset.name}")
            if not dataset.active_version_id:
                print("  No active version")
                continue

            metrics = await service.get_loan_analytics(dataset.id, dataset.active_version_id)
            vis = metrics["visualizations"]

            print("Calculated KPIs:")
            print(f"  Total Loans: {metrics.get('total_loans')}")
            print(f"  Outstanding Exposure: ${metrics.get('outstanding_exposure'):,.2f}")
            print(f"  Average Loan Amount: ${metrics.get('average_loan_amount'):,.2f}")
            print(f"  Repayment Burden Ratio: {metrics.get('repayment_burden_ratio')}")
            print(f"  Delinquency Buckets: {metrics.get('delinquency_buckets')}")
            print(f"  Interest Rate Boxplot: {vis.get('interest_rate_boxplot')}")
            print(f"  Loan Exposure Bars (by status): {vis.get('loan_exposure_bars')}")
            print(f"  Loan Purpose Treemap (first 3 children): {vis.get('loan_purpose_treemap', {}).get('children', [])[:3]}")

if __name__ == '__main__':
    asyncio.run(main())
