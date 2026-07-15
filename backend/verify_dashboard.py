import asyncio
from app.core.database import async_session_maker
from app.services.dashboard_service import DashboardService

async def main():
    async with async_session_maker() as session:
        service = DashboardService(session)
        data = await service.get_risk_dashboard_data()
        print("Risk Dashboard Data:")
        print(f"Total Portfolio Exposure: ${data['total_portfolio_exposure']:,.2f}")
        print(f"Total Delinquency Exposure: ${data['total_delinquency_exposure']:,.2f}")
        print(f"Delinquent Loans Count: {data['delinquent_loans_count']}")
        print(f"Risk Category Distribution: {data['risk_distribution']}")

if __name__ == '__main__':
    asyncio.run(main())
