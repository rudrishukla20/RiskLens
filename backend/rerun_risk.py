import asyncio
from sqlalchemy import select
from app.core.database import async_session_maker
from app.models.dataset import Dataset
from app.models.user import User
from app.services.risk_rule_service import RiskRuleService

async def run():
    async with async_session_maker() as s:
        # Get active admin user
        admin_user = (await s.execute(select(User).where(User.email == "admin@risklens.com"))).scalar_one()
        
        # Get all datasets
        ds = (await s.execute(select(Dataset))).scalars().all()
        
        service = RiskRuleService(s, admin_user)
        
        for d in ds:
            if d.active_version_id:
                print(f"Rerunning Risk Assessment for Dataset: {d.id} ({d.name})")
                await service.run_risk_assessment(d.id, d.active_version_id)
                
        await s.commit()
        print("Commit completed successfully.")

if __name__ == '__main__':
    asyncio.run(run())
