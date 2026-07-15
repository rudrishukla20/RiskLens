import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.core.config import settings
from app.enums.dataset_status import DatasetStatusEnum
from app.enums.validation_status import ValidationStatusEnum
from app.models.dataset import Dataset
from app.models.dataset_version import DatasetVersion


@pytest.fixture
async def sample_dataset(db):
    from sqlalchemy import select

    from app.models.user import User

    admin_user = (await db.execute(select(User).where(User.email == "admin@risklens.com"))).scalar_one()

    dataset_id = uuid.uuid4()
    version_id = uuid.uuid4()

    dataset = Dataset(
        id=dataset_id,
        name="AI Grounding Dataset",
        file_type="CSV",
        original_file_name="ai_test.csv",
        uploaded_by=admin_user.id,
        upload_status=DatasetStatusEnum.UPLOADED,
        validation_status=ValidationStatusEnum.PENDING,
        active_version_id=version_id,
    )
    db.add(dataset)

    version = DatasetVersion(id=version_id, dataset_id=dataset_id, version_number=1, row_count=0, column_count=0)
    db.add(version)
    await db.commit()
    return dataset_id


@pytest.mark.anyio
async def test_disabled_ai_returns_clean_response(client, admin_headers, sample_dataset):
    # Temporarily set provider to disabled
    original_provider = settings.AI_PROVIDER
    settings.AI_PROVIDER = "disabled"

    try:
        res = await client.post(
            "/api/v1/ai-insights/generate",
            headers=admin_headers,
            json={"dataset_id": str(sample_dataset), "analysis_type": "PORTFOLIO", "force_regenerate": True},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["data"]["provider"] == "Portfolio Analytics"
        assert "portfolio contains" in data["data"]["executive_summary"].lower()
    finally:
        settings.AI_PROVIDER = original_provider


@pytest.mark.anyio
async def test_enabled_ai_service_mocked(client, admin_headers, sample_dataset):
    # Temporarily set provider to openai and set dummy key
    original_provider = settings.AI_PROVIDER
    original_key = settings.OPENAI_API_KEY
    settings.AI_PROVIDER = "openai"
    settings.OPENAI_API_KEY = "test_openai_key"

    # Mock response payload
    mock_payload = {
        "choices": [
            {
                "message": {
                    "content": '{"executive_summary": "Mocked portfolio performance summary", "key_findings": ["Healthy margins"], "risk_observations": ["Low concentration"], "recommendations": ["Expand exposure"], "missing_data_caveats": []}'
                }
            }
        ]
    }

    from unittest.mock import MagicMock
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json = MagicMock(return_value=mock_payload)

    try:
        # Patch the targeted AsyncClient inside the service to avoid test client mock collision
        with patch("app.services.ai_insight_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            res = await client.post(
                "/api/v1/ai-insights/generate",
                headers=admin_headers,
                json={"dataset_id": str(sample_dataset), "analysis_type": "PORTFOLIO", "force_regenerate": True},
            )
            assert res.status_code == 200
            data = res.json()
            assert data["success"] is True
            assert data["data"]["provider"] == "openai"
            assert data["data"]["executive_summary"] == "Mocked portfolio performance summary"
            assert data["data"]["key_findings"] == ["Healthy margins"]
            assert data["data"]["risk_observations"] == ["Low concentration"]
            assert data["data"]["recommendations"] == ["Expand exposure"]
    finally:
        settings.AI_PROVIDER = original_provider
        settings.OPENAI_API_KEY = original_key
