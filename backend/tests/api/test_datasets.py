import os

import pytest

from app.core.config import settings

FIXTURE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "fixtures")


@pytest.fixture
def csv_file():
    return os.path.join(FIXTURE_DIR, "sample_credit_dataset.csv")


@pytest.fixture
def xlsx_file():
    return os.path.join(FIXTURE_DIR, "sample_credit_dataset.xlsx")


@pytest.fixture
def json_file():
    return os.path.join(FIXTURE_DIR, "sample_credit_dataset.json")


@pytest.mark.anyio
async def test_csv_upload_works(client, admin_headers, csv_file):
    with open(csv_file, "rb") as f:
        res = await client.post(
            "/api/v1/datasets/upload",
            headers=admin_headers,
            data={"name": "Sample CSV", "description": "My CSV Dataset"},
            files={"file": ("sample_credit_dataset.csv", f, "text/csv")},
        )
    assert res.status_code == 201
    assert res.json()["data"]["file_type"] == "CSV"


@pytest.mark.anyio
async def test_xlsx_upload_works(client, admin_headers, xlsx_file):
    with open(xlsx_file, "rb") as f:
        res = await client.post(
            "/api/v1/datasets/upload",
            headers=admin_headers,
            data={"name": "Sample Excel", "description": "My Excel Dataset"},
            files={
                "file": (
                    "sample_credit_dataset.xlsx",
                    f,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )
    assert res.status_code == 201
    assert res.json()["data"]["file_type"] == "XLSX"


@pytest.mark.anyio
async def test_json_upload_works(client, admin_headers, json_file):
    with open(json_file, "rb") as f:
        res = await client.post(
            "/api/v1/datasets/upload",
            headers=admin_headers,
            data={"name": "Sample JSON", "description": "My JSON Dataset"},
            files={"file": ("sample_credit_dataset.json", f, "application/json")},
        )
    assert res.status_code == 201
    assert res.json()["data"]["file_type"] == "JSON"


@pytest.mark.anyio
async def test_invalid_file_type_rejected(client, admin_headers):
    # Upload a text file as if it were a dataset
    res = await client.post(
        "/api/v1/datasets/upload",
        headers=admin_headers,
        data={"name": "Invalid File", "description": "Should fail"},
        files={"file": ("test.txt", b"some text content", "text/plain")},
    )
    assert res.status_code == 400
    assert res.json()["success"] is False


@pytest.mark.anyio
async def test_oversized_file_rejected(client, admin_headers):
    # Create large dummy content exceeding settings.MAX_UPLOAD_SIZE_MB
    oversized_content = b"a" * (settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024 + 1024)
    res = await client.post(
        "/api/v1/datasets/upload",
        headers=admin_headers,
        data={"name": "Oversized File", "description": "Should fail"},
        files={"file": ("sample.csv", oversized_content, "text/csv")},
    )
    assert res.status_code == 400
    assert "size" in res.json()["message"].lower()


@pytest.mark.anyio
async def test_dataset_list_works(client, admin_headers, csv_file):
    with open(csv_file, "rb") as f:
        await client.post(
            "/api/v1/datasets/upload",
            headers=admin_headers,
            data={"name": "Sample Dataset List", "description": "Listing"},
            files={"file": ("sample_credit_dataset.csv", f, "text/csv")},
        )
    res = await client.get("/api/v1/datasets", headers=admin_headers)
    assert res.status_code == 200
    assert len(res.json()["data"]["items"]) > 0


@pytest.mark.anyio
async def test_schema_mapping_confirmation_works(client, admin_headers, csv_file):
    # 1. Upload dataset to get ID
    with open(csv_file, "rb") as f:
        upload_res = await client.post(
            "/api/v1/datasets/upload",
            headers=admin_headers,
            data={"name": "Mapping Dataset", "description": "For mapping confirm"},
            files={"file": ("sample_credit_dataset.csv", f, "text/csv")},
        )
    dataset_id = upload_res.json()["data"]["id"]

    # 2. Call confirm endpoint
    res = await client.post(
        f"/api/v1/datasets/{dataset_id}/schema-mapping/confirm",
        headers=admin_headers,
        json={
            "mappings": [
                {"original_column_name": "customer_id", "canonical_field": "borrower_id"},
                {"original_column_name": "annual_income", "canonical_field": "annual_income"},
            ]
        },
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert len(data) == 2
    assert data[0]["canonical_field"] in ("borrower_id", "annual_income")


@pytest.mark.anyio
async def test_schema_inference_works(csv_file):
    import pandas as pd

    from app.ingestion.schema_inferer import infer_schema

    df = pd.read_csv(csv_file)
    inferred = infer_schema(df)
    assert len(inferred) > 0
    # verify some fields
    col_names = [col.original_name for col in inferred]
    assert "age" in col_names or "customer_id" in col_names
