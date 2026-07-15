import uuid

import pytest

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
        name="Reports Test Dataset",
        file_type="CSV",
        original_file_name="reports_test.csv",
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
async def test_generate_pdf_report(client, admin_headers, sample_dataset):
    res = await client.post(
        "/api/v1/reports/generate",
        headers=admin_headers,
        json={
            "dataset_id": str(sample_dataset),
            "report_type": "PORTFOLIO_REPORT",
            "title": "Portfolio Performance Report",
            "export_format": "PDF",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["data"]["export_format"] == "PDF"
    assert data["data"]["title"] is not None


@pytest.mark.anyio
async def test_generate_xlsx_report(client, admin_headers, sample_dataset):
    res = await client.post(
        "/api/v1/reports/generate",
        headers=admin_headers,
        json={
            "dataset_id": str(sample_dataset),
            "report_type": "DATA_QUALITY_REPORT",
            "title": "Data Quality Audit Report",
            "export_format": "XLSX",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["data"]["export_format"] == "XLSX"


@pytest.mark.anyio
async def test_generate_csv_report(client, admin_headers, sample_dataset):
    res = await client.post(
        "/api/v1/reports/generate",
        headers=admin_headers,
        json={
            "dataset_id": str(sample_dataset),
            "report_type": "CREDIT_RISK_REPORT",
            "title": "Credit Risk Summary Report",
            "export_format": "CSV",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["data"]["export_format"] == "CSV"


@pytest.mark.anyio
async def test_list_reports_and_download(client, admin_headers, sample_dataset):
    # 1. Generate a report first
    gen_res = await client.post(
        "/api/v1/reports/generate",
        headers=admin_headers,
        json={
            "dataset_id": str(sample_dataset),
            "report_type": "PORTFOLIO_REPORT",
            "title": "Portfolio Performance CSV Report",
            "export_format": "CSV",
        },
    )
    report_id = gen_res.json()["data"]["id"]

    # 2. List reports
    list_res = await client.get("/api/v1/reports", headers=admin_headers)
    assert list_res.status_code == 200
    assert len(list_res.json()["data"]["items"]) > 0

    # 3. Get individual report metadata
    get_res = await client.get(f"/api/v1/reports/{report_id}", headers=admin_headers)
    assert get_res.status_code == 200
    assert get_res.json()["data"]["id"] == report_id

    # 4. Download report file
    dl_res = await client.get(f"/api/v1/reports/{report_id}/download", headers=admin_headers)
    assert dl_res.status_code == 200
    assert dl_res.headers["content-type"].startswith("text/csv")
    assert len(dl_res.content) > 0
