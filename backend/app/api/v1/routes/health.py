from fastapi import APIRouter

from app.responses.envelope import ResponseEnvelope, build_success_response

router = APIRouter()


@router.get("/health", response_model=ResponseEnvelope)
async def health_check():
    """Basic service availability status route."""
    return build_success_response(data={"status": "healthy"}, message="Service is healthy")
