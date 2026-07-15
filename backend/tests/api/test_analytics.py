import uuid
from datetime import datetime

import pytest

from app.analytics.risk_rule_engine import RiskRuleEngine
from app.enums.dataset_status import DatasetStatusEnum
from app.enums.validation_status import ValidationStatusEnum
from app.models.borrower import Borrower
from app.models.dataset import Dataset
from app.models.dataset_version import DatasetVersion
from app.models.loan import Loan


@pytest.mark.anyio
async def test_risk_dashboard_kpis(client, admin_headers):
    res = await client.get("/api/v1/analytics/dashboard", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "total_portfolio_exposure" in data["data"]


@pytest.mark.anyio
async def test_analytics_endpoints_empty_dataset(client, db, admin_headers):
    from sqlalchemy import select

    from app.models.user import User

    admin_user = (await db.execute(select(User).where(User.email == "admin@risklens.com"))).scalar_one()

    # Create empty dataset in db
    dataset_id = uuid.uuid4()
    version_id = uuid.uuid4()

    dataset = Dataset(
        id=dataset_id,
        name="Empty Analytics Dataset",
        file_type="CSV",
        original_file_name="empty_test.csv",
        uploaded_by=admin_user.id,
        upload_status=DatasetStatusEnum.UPLOADED,
        validation_status=ValidationStatusEnum.PENDING,
        active_version_id=version_id,
    )
    db.add(dataset)

    version = DatasetVersion(id=version_id, dataset_id=dataset_id, version_number=1, row_count=0, column_count=0)
    db.add(version)
    await db.commit()

    db.expire_all()
    # Query trends
    res_trends = await client.get(f"/api/v1/analytics/trends?dataset_id={dataset_id}", headers=admin_headers)
    assert res_trends.status_code == 200
    assert res_trends.json()["data"]["status"] == "unavailable"
    assert "empty" in res_trends.json()["data"]["message"]

    # Query vintage
    res_vintage = await client.get(f"/api/v1/analytics/vintage?dataset_id={dataset_id}", headers=admin_headers)
    assert res_vintage.status_code == 200
    assert res_vintage.json()["data"]["status"] == "unavailable"
    assert "empty" in res_vintage.json()["data"]["message"]

    # Query risk migration
    res_mig = await client.get(f"/api/v1/analytics/migration?dataset_id={dataset_id}", headers=admin_headers)
    assert res_mig.status_code == 200
    assert res_mig.json()["data"]["status"] == "unavailable"
    assert "multiple versions" in res_mig.json()["data"]["message"]


@pytest.mark.anyio
async def test_analytics_endpoints_missing_dates(client, db, admin_headers):
    from sqlalchemy import select

    from app.models.user import User

    admin_user = (await db.execute(select(User).where(User.email == "admin@risklens.com"))).scalar_one()

    # Create dataset with loans but NO disbursement date
    dataset_id = uuid.uuid4()
    version_id = uuid.uuid4()

    dataset = Dataset(
        id=dataset_id,
        name="No Dates Dataset",
        file_type="CSV",
        original_file_name="nodates_test.csv",
        uploaded_by=admin_user.id,
        upload_status=DatasetStatusEnum.UPLOADED,
        validation_status=ValidationStatusEnum.PENDING,
        active_version_id=version_id,
    )
    db.add(dataset)

    version = DatasetVersion(id=version_id, dataset_id=dataset_id, version_number=1, row_count=1, column_count=2)
    db.add(version)

    borrower_id = uuid.uuid4()
    borrower = Borrower(
        id=borrower_id,
        dataset_id=dataset_id,
        version_id=version_id,
        source_borrower_id="B1",
        age=30,
        gender="M",
        income=50000.0,
        employment_type="Full-time",
    )
    db.add(borrower)

    loan = Loan(
        id=uuid.uuid4(),
        dataset_id=dataset_id,
        version_id=version_id,
        borrower_id=borrower_id,
        loan_amount=10000.0,
        outstanding_amount=9000.0,
        loan_purpose="Debt consolidation",
        disbursement_date=None,  # Missing Date!
    )
    db.add(loan)
    await db.commit()

    db.expire_all()
    # Query trends
    res_trends = await client.get(f"/api/v1/analytics/trends?dataset_id={dataset_id}", headers=admin_headers)
    assert res_trends.status_code == 200
    assert res_trends.json()["data"]["status"] == "unavailable"
    assert "date field" in res_trends.json()["data"]["message"]

    # Query vintage
    res_vintage = await client.get(f"/api/v1/analytics/vintage?dataset_id={dataset_id}", headers=admin_headers)
    assert res_vintage.status_code == 200
    assert res_vintage.json()["data"]["status"] == "unavailable"
    assert "date field" in res_vintage.json()["data"]["message"]


@pytest.mark.anyio
async def test_analytics_deterministic_generation(client, db, admin_headers):
    from sqlalchemy import select

    from app.models.user import User

    admin_user = (await db.execute(select(User).where(User.email == "admin@risklens.com"))).scalar_one()

    # Populate valid database records to run risk assessment
    dataset_id = uuid.uuid4()
    version_id = uuid.uuid4()

    dataset = Dataset(
        id=dataset_id,
        name="Valid Assessment Dataset",
        file_type="CSV",
        original_file_name="valid_test.csv",
        uploaded_by=admin_user.id,
        upload_status=DatasetStatusEnum.UPLOADED,
        validation_status=ValidationStatusEnum.PENDING,
        active_version_id=version_id,
    )
    db.add(dataset)

    version = DatasetVersion(id=version_id, dataset_id=dataset_id, version_number=1, row_count=1, column_count=2)
    db.add(version)

    borrower_id = uuid.uuid4()
    borrower = Borrower(
        id=borrower_id,
        dataset_id=dataset_id,
        version_id=version_id,
        source_borrower_id="B2",
        age=35,
        gender="F",
        income=80000.0,
        employment_type="Full-time",
    )
    db.add(borrower)

    loan = Loan(
        id=uuid.uuid4(),
        dataset_id=dataset_id,
        version_id=version_id,
        borrower_id=borrower_id,
        loan_amount=20000.0,
        outstanding_amount=18000.0,
        loan_purpose="Education",
        disbursement_date=datetime(2025, 6, 15),
    )
    db.add(loan)
    await db.commit()

    # Call Risk Rule Engine directly to generate deterministic assessment
    engine = RiskRuleEngine(db)
    result = await engine.assess_risk(dataset_id, version_id)
    assert "risk_score" in result
    await db.commit()

    db.expire_all()
    # Call API to verify stored risk assessment
    res_risk = await client.get(f"/api/v1/analytics/risk?dataset_id={dataset_id}", headers=admin_headers)
    assert res_risk.status_code == 200
    assert len(res_risk.json()["data"]) == 1
    assert res_risk.json()["data"][0]["borrower_id"] == str(borrower_id)
