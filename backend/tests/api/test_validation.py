import uuid

import pytest

from app.analytics.data_quality_engine import DataQualityEngine
from app.enums.dataset_status import DatasetStatusEnum
from app.enums.validation_status import ValidationStatusEnum
from app.models.dataset import Dataset
from app.models.dataset_version import DatasetVersion
from app.models.raw_record import RawRecord
from app.models.schema_mapping import SchemaMapping


@pytest.mark.anyio
async def test_data_validation_detection(client, db, admin_headers):
    from sqlalchemy import select

    from app.models.user import User

    admin_user = (await db.execute(select(User).where(User.email == "admin@risklens.com"))).scalar_one()

    # 1. Create a dummy dataset in db
    dataset_id = uuid.uuid4()
    version_id = uuid.uuid4()

    dataset = Dataset(
        id=dataset_id,
        name="Validation Test Dataset",
        file_type="CSV",
        original_file_name="validation_test.csv",
        uploaded_by=admin_user.id,
        upload_status=DatasetStatusEnum.UPLOADED,
        validation_status=ValidationStatusEnum.PENDING,
        active_version_id=version_id,
    )
    db.add(dataset)

    version = DatasetVersion(id=version_id, dataset_id=dataset_id, version_number=1, row_count=3, column_count=5)
    db.add(version)

    # 2. Add schema mappings
    mappings = [
        {"col": "col_borrower", "canon": "borrower_id"},
        {"col": "col_income", "canon": "income"},
        {"col": "col_employment", "canon": "employment_type"},
        {"col": "col_loan_amount", "canon": "loan_amount"},
        {"col": "col_loan_purpose", "canon": "loan_purpose"},
    ]
    for idx, m in enumerate(mappings):
        sm = SchemaMapping(
            id=uuid.uuid4(),
            dataset_id=dataset_id,
            version_id=version_id,
            original_column_name=m["col"],
            canonical_field=m["canon"],
            confidence_score=1.0,
            mapping_source="MANUAL",
        )
        db.add(sm)

    # 3. Add RawRecords with validation issues
    # - Record 1: Valid
    # - Record 2: Missing required income
    # - Record 3: Duplicate borrower_id B123 and invalid loan_amount datatype (None in canonical)
    raw_records_data = [
        {
            "raw": {
                "col_borrower": "B123",
                "col_income": "50000",
                "col_employment": "Full-time",
                "col_loan_amount": "10000",
                "col_loan_purpose": "Education",
            },
            "canon": {
                "borrower_id": "B123",
                "income": 50000.0,
                "employment_type": "Full-time",
                "loan_amount": 10000.0,
                "loan_purpose": "Education",
            },
            "row": 1,
        },
        {
            "raw": {
                "col_borrower": "B124",
                "col_income": None,
                "col_employment": "Part-time",
                "col_loan_amount": "20000",
                "col_loan_purpose": "Debt consolidation",
            },
            "canon": {
                "borrower_id": "B124",
                "income": None,
                "employment_type": "Part-time",
                "loan_amount": 20000.0,
                "loan_purpose": "Debt consolidation",
            },
            "row": 2,
        },
        {
            "raw": {
                "col_borrower": "B123",
                "col_income": "60000",
                "col_employment": "Full-time",
                "col_loan_amount": "INVALID_FLOAT",
                "col_loan_purpose": "Car",
            },
            "canon": {
                "borrower_id": "B123",
                "income": 60000.0,
                "employment_type": "Full-time",
                "loan_amount": None,
                "loan_purpose": "Car",
            },
            "row": 3,
        },
    ]
    for r in raw_records_data:
        rr = RawRecord(
            id=uuid.uuid4(),
            dataset_id=dataset_id,
            version_id=version_id,
            source_row_number=r["row"],
            raw_data_json=r["raw"],
            canonical_data_json=r["canon"],
        )
        db.add(rr)

    await db.commit()

    # 4. Trigger validation engine directly
    dq_engine = DataQualityEngine(db)
    await dq_engine.run_validation(dataset_id, version_id)
    await db.commit()

    db.expire_all()
    # 5. Get latest validation run info via API
    res_latest = await client.get(f"/api/v1/datasets/{dataset_id}/validation/latest", headers=admin_headers)
    assert res_latest.status_code == 200
    latest_data = res_latest.json()
    assert latest_data["success"] is True
    assert latest_data["data"]["missing_value_count"] == 1
    assert latest_data["data"]["duplicate_count"] == 1
    assert latest_data["data"]["invalid_type_count"] == 1

    # 6. Query granular validation issues via API
    res_issues = await client.get(f"/api/v1/datasets/{dataset_id}/validation/issues", headers=admin_headers)
    assert res_issues.status_code == 200
    issues_data = res_issues.json()
    assert issues_data["success"] is True

    types = [issue["issue_type"] for issue in issues_data["data"]]
    assert "MISSING_VALUE" in types
    assert "DUPLICATE" in types
    assert "INVALID_TYPE" in types
