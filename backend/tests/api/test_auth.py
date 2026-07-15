import pytest


@pytest.mark.anyio
async def test_login_success(client):
    # Standard login using seeded admin credentials
    res = await client.post(
        "/api/v1/auth/login", json={"email": "admin@risklens.com", "password": "ChangeMeStrongPassword123!"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "access_token" in data["data"]
    assert "refresh_token" in data["data"]


@pytest.mark.anyio
async def test_login_failure(client):
    res = await client.post("/api/v1/auth/login", json={"email": "admin@risklens.com", "password": "WrongPassword123!"})
    assert res.status_code == 401
    data = res.json()
    assert data["success"] is False
    assert data["error"]["code"] == "AUTH_UNAUTHORIZED"


@pytest.mark.anyio
async def test_inactive_user_login_blocked(client, db, admin_headers):
    # Create a user and set status to DEACTIVATED
    res = await client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={
            "email": "inactive@risklens.com",
            "full_name": "Inactive User",
            "password": "DeactivatedPassword123!",
            "role_code": "CREDIT_RISK_GOVERNANCE_OFFICER",
        },
    )
    assert res.status_code == 201

    # Deactivate the user
    user_id = res.json()["data"]["id"]
    deact_res = await client.patch(f"/api/v1/users/{user_id}/deactivate", headers=admin_headers)
    assert deact_res.status_code == 200

    # Try login
    login_res = await client.post(
        "/api/v1/auth/login", json={"email": "inactive@risklens.com", "password": "DeactivatedPassword123!"}
    )
    assert login_res.status_code == 401
    assert "inactive" in login_res.json()["message"].lower()


@pytest.mark.anyio
async def test_refresh_token_success(client):
    login_res = await client.post(
        "/api/v1/auth/login", json={"email": "admin@risklens.com", "password": "ChangeMeStrongPassword123!"}
    )
    refresh_token = login_res.json()["data"]["refresh_token"]

    res = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert res.status_code == 200
    assert "access_token" in res.json()["data"]


@pytest.mark.anyio
async def test_logout_revokes_token(client, admin_headers):
    login_res = await client.post(
        "/api/v1/auth/login", json={"email": "admin@risklens.com", "password": "ChangeMeStrongPassword123!"}
    )
    refresh_token = login_res.json()["data"]["refresh_token"]
    headers = {"Authorization": f"Bearer {login_res.json()['data']['access_token']}"}

    # Logout
    logout_res = await client.post("/api/v1/auth/logout", headers=headers, json={"refresh_token": refresh_token})
    assert logout_res.status_code == 200

    # Refreshing should now fail
    refresh_res = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_res.status_code == 401


@pytest.mark.anyio
async def test_me_endpoint(client, admin_headers):
    res = await client.get("/api/v1/auth/me", headers=admin_headers)
    assert res.status_code == 200
    assert res.json()["data"]["email"] == "admin@risklens.com"


@pytest.mark.anyio
async def test_invalid_token_returns_401_envelope(client):
    res = await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid_token"})
    assert res.status_code == 401
    data = res.json()
    assert data["success"] is False
    assert data["error"]["code"] == "AUTH_UNAUTHORIZED"
