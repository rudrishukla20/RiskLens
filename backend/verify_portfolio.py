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

            metrics = await service.get_portfolio_analytics(dataset.id, dataset.active_version_id)
            vis = metrics["visualizations"]

            print("Calculated Portfolio KPIs:")
            print(f"  Portfolio Value: ${metrics.get('portfolio_value'):,.2f}")
            print(f"  Outstanding Exposure: ${metrics.get('outstanding_exposure'):,.2f}")
            print(f"  High-Risk Exposure: ${metrics.get('high_risk_exposure'):,.2f}")
            print(f"  High-Risk Exposure %: {metrics.get('high_risk_exposure_percentage')}%")
            print(f"  Concentration Index (HHI): {metrics.get('concentration_index')}")
            print(f"  Diversification Index: {metrics.get('diversification_index')}")
            print("  Portfolio Composition Donut:")
            for k, v in vis.get('portfolio_composition_donut', {}).items():
                print(f"    {k}: {v}")
            print("  Exposure Distribution (first 3 regions):")
            for k, v in list(vis.get('exposure_distribution', {}).get('regions', {}).items())[:3]:
                print(f"    {k}: ${v:,.2f}")
            print("  Exposure Distribution (income bands):")
            for k, v in vis.get('exposure_distribution', {}).get('income_bands', {}).items():
                print(f"    {k}: ${v:,.2f}")
            print("  Region Risk Heatmap Matrix (first 4 items):")
            for item in vis.get('region_risk_heatmap', {}).get('matrix', [])[:4]:
                print(f"    {item}")

if __name__ == '__main__':
    asyncio.run(main())
