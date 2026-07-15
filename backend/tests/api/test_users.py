import uuid

import pytest


@pytest.mark.anyio
async def test_admin_create_user(client, admin_headers):
    email = f"test_{uuid.uuid4().hex[:6]}@risklens.com"
    res = await client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={
            "email": email,
            "full_name": "Test User",
            "password": "SecurePassword123!",
            "role_code": "CREDIT_RISK_GOVERNANCE_OFFICER",
        },
    )
    assert res.status_code == 201
    assert res.json()["data"]["email"] == email


@pytest.mark.anyio
async def test_admin_update_user(client, admin_headers):
    # First create
    email = f"test_{uuid.uuid4().hex[:6]}@risklens.com"
    create_res = await client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={
            "email": email,
            "full_name": "Test User",
            "password": "SecurePassword123!",
            "role_code": "CREDIT_RISK_GOVERNANCE_OFFICER",
        },
    )
    user_id = create_res.json()["data"]["id"]

    # Update
    res = await client.patch(f"/api/v1/users/{user_id}", headers=admin_headers, json={"full_name": "Updated Name"})
    assert res.status_code == 200
    assert res.json()["data"]["full_name"] == "Updated Name"


@pytest.mark.anyio
async def test_admin_deactivate_user(client, admin_headers):
    # First create
    email = f"test_{uuid.uuid4().hex[:6]}@risklens.com"
    create_res = await client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={
            "email": email,
            "full_name": "Test User",
            "password": "SecurePassword123!",
            "role_code": "CREDIT_RISK_GOVERNANCE_OFFICER",
        },
    )
    user_id = create_res.json()["data"]["id"]

    # Deactivate
    res = await client.patch(f"/api/v1/users/{user_id}/deactivate", headers=admin_headers)
    assert res.status_code == 200
    assert res.json()["data"]["status"] == "DEACTIVATED"


@pytest.mark.anyio
async def test_non_admin_denied_user_management(client, crgo_headers):
    # Try create
    res_create = await client.post(
        "/api/v1/users",
        headers=crgo_headers,
        json={
            "email": "denied@risklens.com",
            "full_name": "Denied User",
            "password": "SecurePassword123!",
            "role_code": "CREDIT_RISK_GOVERNANCE_OFFICER",
        },
    )
    assert res_create.status_code == 403

    # Try update
    random_uuid = str(uuid.uuid4())
    res_update = await client.patch(
        f"/api/v1/users/{random_uuid}", headers=crgo_headers, json={"full_name": "Should Fail"}
    )
    assert res_update.status_code == 403

    # Try deactivate
    res_deact = await client.patch(f"/api/v1/users/{random_uuid}/deactivate", headers=crgo_headers)
    assert res_deact.status_code == 403
