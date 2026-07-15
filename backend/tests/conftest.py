import os

import pytest

# Configure APP_ENV and TEST_DATABASE_URL to use SQLite for tests
os.environ["APP_ENV"] = "test"
os.environ["TEST_DATABASE_URL"] = "sqlite+aiosqlite:///test_risklens.db"

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.core.rate_limit import limiter
from app.main import app
from app.seed.run_seed import seed_system_settings
from app.seed.seed_admin import seed_admin
from app.seed.seed_roles import seed_roles

limiter.enabled = False

# Define test database engine
test_engine = create_async_engine("sqlite+aiosqlite:///test_risklens.db", echo=False)
TestingSessionLocal = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
async def setup_db():
    # Run migrations/create tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # Seed roles and admin
    async with TestingSessionLocal() as session:
        await seed_roles(session)
        await seed_admin(session)
        await seed_system_settings(session)
        await session.commit()

    yield

    # Cleanup DB file
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db():
    async with TestingSessionLocal() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def client(db):
    async def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def admin_token(client):
    res = await client.post(
        "/api/v1/auth/login", json={"email": "admin@risklens.com", "password": "ChangeMeStrongPassword123!"}
    )
    assert res.status_code == 200
    return res.json()["data"]["access_token"]


@pytest.fixture
async def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
async def crgo_user(client, admin_headers):
    email = "crgo@risklens.com"
    # To prevent duplicate insert issues in tests, try creating and catch conflicts
    await client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={
            "email": email,
            "full_name": "CRGO User",
            "password": "CRGOPassword123!",
            "role_code": "CREDIT_RISK_GOVERNANCE_OFFICER",
        },
    )
    return {"email": email, "password": "CRGOPassword123!"}


@pytest.fixture
async def crgo_headers(client, crgo_user):
    res = await client.post("/api/v1/auth/login", json={"email": crgo_user["email"], "password": crgo_user["password"]})
    assert res.status_code == 200
    token = res.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}
