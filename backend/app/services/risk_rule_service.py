import uuid
from typing import Any, Dict

from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.risk_rule_engine import RiskRuleEngine
from app.core.deps import log_audit_action
from app.enums.audit_action import AuditActionEnum
from app.models.user import User


class RiskRuleService:
    """
    Service coordinating the risk rule assessment workflow, persistence, and audit logging.
    """

    def __init__(self, db: AsyncSession, user: User) -> None:
        self.db = db
        self.user = user

    async def run_risk_assessment(self, dataset_id: uuid.UUID, version_id: uuid.UUID) -> Dict[str, Any]:
        """
        Coordinates the execution of rule-based risk scoring, persistence, and audit logs logging.
        """
        engine = RiskRuleEngine(self.db)

        try:
            # Execute assessment logic and DB insertions
            result = await engine.assess_risk(dataset_id, version_id)

            # Log audit event
            await log_audit_action(
                self.db,
                user_id=self.user.id,
                action=AuditActionEnum.ANALYTICS_GENERATED,
                module_name="analytics",
                resource_type="Dataset",
                resource_id=str(dataset_id),
                details={"version_id": str(version_id), "analytics_type": "Risk Rules"},
            )

            # Flush changes in session (caller or route handler commits transaction)
            await self.db.flush()
            return result
        except Exception as e:
            # Let the database handler rollback if a critical error occurs
            raise e
