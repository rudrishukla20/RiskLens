from fastapi import APIRouter

from app.api.v1.routes.admin_dashboard import router as admin_router
from app.api.v1.routes.ai_insights import router as ai_insights_router
from app.api.v1.routes.analytics import router as analytics_router
from app.api.v1.routes.audit_logs import router as audit_logs_router
from app.api.v1.routes.auth import router as auth_router
from app.api.v1.routes.dataset_sources import router as dataset_sources_router
from app.api.v1.routes.datasets import router as datasets_router
from app.api.v1.routes.documents import router as documents_router
from app.api.v1.routes.health import router as health_router
from app.api.v1.routes.profiling import router as profiling_router
from app.api.v1.routes.reports import router as reports_router
from app.api.v1.routes.schema_mapping import router as schema_mapping_router
from app.api.v1.routes.users import router as users_router
from app.api.v1.routes.validation import router as validation_router

api_router = APIRouter()

# Register Auth, Admin, and User routers
api_router.include_router(auth_router, prefix="/auth", tags=["Auth"])
api_router.include_router(admin_router, prefix="/admin", tags=["Admin"])
api_router.include_router(users_router, prefix="/users", tags=["Users"])

# Register Dataset routers (some define full "/datasets" paths, some are mounted with prefix)
api_router.include_router(datasets_router, prefix="/datasets", tags=["Datasets"])
api_router.include_router(schema_mapping_router, tags=["Schema Mapping"])
api_router.include_router(validation_router, tags=["Validation"])
api_router.include_router(profiling_router, tags=["Profiling"])

# Register Documents, Analytics, AI Insights, Reports
api_router.include_router(documents_router, prefix="/documents", tags=["Documents"])
api_router.include_router(analytics_router, prefix="/analytics", tags=["Analytics"])
api_router.include_router(ai_insights_router, prefix="/ai-insights", tags=["AI Insights"])
api_router.include_router(reports_router, prefix="/reports", tags=["Reports"])

# Register Audit, Dataset Sources, Health
api_router.include_router(audit_logs_router, prefix="/audit", tags=["Audit"])
api_router.include_router(dataset_sources_router, prefix="/public-dataset-sources", tags=["Dataset Sources"])
api_router.include_router(health_router, tags=["Health"])
