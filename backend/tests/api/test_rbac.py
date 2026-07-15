import pytest

from app.core.deps import require_governance
from app.exceptions.base import AuthorizationException
from app.models.role import Role
from app.models.user import User


@pytest.mark.anyio
async def test_admin_can_access_admin_routes(client, admin_headers):
    res = await client.get("/api/v1/admin/dashboard", headers=admin_headers)
    assert res.status_code == 200
    assert res.json()["success"] is True


@pytest.mark.anyio
async def test_crgo_cannot_access_admin_routes(client, crgo_headers):
    res = await client.get("/api/v1/admin/dashboard", headers=crgo_headers)
    assert res.status_code == 403
    assert res.json()["success"] is False
    assert res.json()["error"]["code"] == "AUTH_FORBIDDEN"


@pytest.mark.anyio
async def test_unauthenticated_user_blocked(client):
    res = await client.get("/api/v1/admin/dashboard")
    assert res.status_code == 401
    assert res.json()["success"] is False


@pytest.mark.anyio
async def test_no_roles_endpoint_exists(client, admin_headers):
    res = await client.get("/api/v1/roles", headers=admin_headers)
    assert res.status_code == 404


@pytest.mark.anyio
async def test_admin_blocked_by_governance_guard():
    # Verify that an Admin user is blocked by the governance-only checker
    admin_user = User(role=Role(code="ADMIN"))
    with pytest.raises(AuthorizationException) as exc_info:
        require_governance(admin_user)
    assert "Insufficient privileges" in str(exc_info.value.message)
