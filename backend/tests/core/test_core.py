import logging

import pytest

from app.seed.run_seed import seed_system_settings
from app.seed.seed_admin import seed_admin
from app.seed.seed_roles import seed_roles


@pytest.mark.anyio
async def test_standard_envelope_everywhere(client, admin_headers):
    # Test success envelope
    res = await client.get("/api/v1/auth/me", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()
    assert "success" in data
    assert data["success"] is True
    assert "meta" in data
    assert "request_id" in data["meta"]
    assert "timestamp" in data["meta"]

    # Test error envelope
    res_err = await client.post(
        "/api/v1/auth/login", json={"email": "admin@risklens.com", "password": "WrongPassword123!"}
    )
    assert res_err.status_code == 401
    data_err = res_err.json()
    assert "success" in data_err
    assert data_err["success"] is False
    assert "error" in data_err
    assert "code" in data_err["error"]


@pytest.mark.anyio
async def test_exception_handlers_normalize_errors(client):
    # Call an invalid route to trigger 404
    res = await client.get("/api/v1/non-existent-route-path")
    assert res.status_code == 404
    data = res.json()
    assert data["success"] is False
    assert data["error"]["code"] == "NOT_FOUND"


@pytest.mark.anyio
async def test_rate_limit_returns_429(client):
    from app.core.rate_limit import limiter

    limiter.enabled = True
    try:
        triggered = False
        for _ in range(10):
            res = await client.post(
                "/api/v1/auth/login", json={"email": "rate@limit.com", "password": "WrongPassword123!"}
            )
            if res.status_code == 429:
                triggered = True
                data = res.json()
                assert data["success"] is False
                assert data["error"]["code"] == "RATE_LIMIT_EXCEEDED"
                break
        assert triggered, "Rate limiting was not triggered after 10 rapid calls"
    finally:
        limiter.enabled = False


@pytest.mark.anyio
async def test_request_id_exists(client):
    res = await client.get("/health")
    assert res.status_code == 200
    assert "request_id" in res.json()["meta"]
    assert len(res.json()["meta"]["request_id"]) > 0


@pytest.mark.anyio
async def test_logging_handler_configured():
    # Verify that risklens logger is configured with handlers
    risklens_logger = logging.getLogger("risklens")
    assert len(risklens_logger.handlers) > 0


@pytest.mark.anyio
async def test_seed_scripts_idempotent(db):
    # Running seeds multiple times should be successful and not raise exceptions
    await seed_roles(db)
    await seed_admin(db)
    await seed_system_settings(db)
    await db.commit()

    # Second run to test idempotency
    await seed_roles(db)
    await seed_admin(db)
    await seed_system_settings(db)
    await db.commit()
