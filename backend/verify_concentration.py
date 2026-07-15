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

            metrics = await service.get_concentration_analytics(dataset.id, dataset.active_version_id)
            vis = metrics["visualizations"]

            print("Calculated Concentration KPIs:")
            print(f"  HHI: {metrics.get('herfindahl_hirschman_index')}")
            print(f"  HHI by dimension: {metrics.get('hhi_by_dimension')}")
            print(f"  Top borrower concentration: {metrics.get('top_borrower_concentration')}%")
            print(f"  Top region concentration: {metrics.get('top_region_concentration')}%")
            print(f"  Top loan purpose concentration: {metrics.get('top_loan_purpose_concentration')}%")
            print(f"  Top employment concentration: {metrics.get('top_employment_segment_concentration')}%")
            print(f"  Top income concentration: {metrics.get('top_income_band_concentration')}%")
            print(f"  High-risk concentration: {metrics.get('high_risk_concentration')}%")
            
            print("  Pareto Chart data (first 3 regions):")
            for item in vis.get('pareto_chart', [])[:3]:
                print(f"    {item}")
            print("  Treemap Purposes (first 3 children):")
            for item in vis.get('treemap', {}).get('purposes', {}).get('children', [])[:3]:
                print(f"    {item}")
            print("  Ranked Exposure Table (first 3 records):")
            for item in vis.get('ranked_exposure_table', [])[:3]:
                print(f"    {item}")

if __name__ == '__main__':
    asyncio.run(main())
