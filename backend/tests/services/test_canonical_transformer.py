import uuid
import pytest
import pandas as pd
from datetime import date
from sqlalchemy import select

from app.models.dataset import Dataset
from app.models.dataset_version import DatasetVersion
from app.models.dataset_column import DatasetColumn
from app.models.schema_mapping import SchemaMapping
from app.models.user import User
from app.models.loan import Loan
from app.models.raw_record import RawRecord
from app.enums.dataset_status import DatasetStatusEnum
from app.enums.validation_status import ValidationStatusEnum
from app.ingestion.canonical_transformer import transform_and_populate

@pytest.mark.anyio
async def test_canonical_date_fallback_chain(db):
    admin_user = (await db.execute(select(User).where(User.email == "admin@risklens.com"))).scalar_one()

    # 1. Setup dataset and version
    dataset_id = uuid.uuid4()
    version_id = uuid.uuid4()
    
    dataset = Dataset(
        id=dataset_id,
        name="Fallback Date Test Dataset",
        file_type="CSV",
        original_file_name="fallback_test.csv",
        uploaded_by=admin_user.id,
        upload_status=DatasetStatusEnum.UPLOADED,
        validation_status=ValidationStatusEnum.PENDING,
        active_version_id=version_id,
    )
    db.add(dataset)
    
    version = DatasetVersion(
        id=version_id,
        dataset_id=dataset_id,
        version_number=1,
        row_count=5,
        column_count=8
    )
    db.add(version)
    await db.commit()

    # 2. Add Dataset Columns metadata to db
    columns = [
        ("borrower_id", "string", "borrower_id"),
        ("loan_amount", "float", "loan_amount"),
        ("disb_dt", "datetime", "disbursement_date"),
        ("app_date", "datetime", None),
        ("first_pay_dt", "datetime", None),
        ("other_dt_b", "datetime", None),
        ("other_dt_a", "datetime", None),
        ("non_date_col", "string", None)
    ]
    for orig, dtype, canon in columns:
        dc = DatasetColumn(
            id=uuid.uuid4(),
            dataset_id=dataset_id,
            version_id=version_id,
            original_column_name=orig,
            canonical_column_name=canon,
            inferred_data_type=dtype,
            mapped_data_type=dtype,
            is_mapped=canon is not None,
            is_required=orig in ("borrower_id", "loan_amount")
        )
        db.add(dc)

    # 3. Add confirmed Schema Mappings
    mappings = [
        ("borrower_id", "borrower_id"),
        ("loan_amount", "loan_amount"),
        ("disb_dt", "disbursement_date")
    ]
    for orig, canon in mappings:
        sm = SchemaMapping(
            id=uuid.uuid4(),
            dataset_id=dataset_id,
            version_id=version_id,
            original_column_name=orig,
            canonical_field=canon,
            mapping_source="MANUAL",
            confirmed_by=admin_user.id
        )
        db.add(sm)
        
    await db.commit()

    # 4. Create raw DataFrame with scenarios:
    # Row 0: Mapped disb_dt is present. Uses disb_dt.
    # Row 1: Mapped disb_dt is null, but app_date (application date) is present. Uses app_date.
    # Row 2: Mapped disb_dt and app_date are null, but first_pay_dt (first payment date) is present. Uses first_pay_dt.
    # Row 3: disbursement_date, application, and first payment are all null, but other_dt_a and other_dt_b (other date-like columns) are present.
    #        Since other_dt_a and other_dt_b are both profiled as datetime, it checks them in alphabetical order. 
    #        other_dt_a comes first alphabetically, so it should use other_dt_a.
    # Row 4: No date columns have values. Should fallback to null and set date_is_synthetic = True.
    df = pd.DataFrame([
        {
            "borrower_id": "B1",
            "loan_amount": 1000.0,
            "disb_dt": "2026-01-01",
            "app_date": "2026-01-02",
            "first_pay_dt": "2026-01-03",
            "other_dt_b": "2026-01-04",
            "other_dt_a": "2026-01-05",
            "non_date_col": "hello"
        },
        {
            "borrower_id": "B2",
            "loan_amount": 2000.0,
            "disb_dt": None,
            "app_date": "2026-02-02",
            "first_pay_dt": "2026-02-03",
            "other_dt_b": "2026-02-04",
            "other_dt_a": "2026-02-05",
            "non_date_col": "hello"
        },
        {
            "borrower_id": "B3",
            "loan_amount": 3000.0,
            "disb_dt": None,
            "app_date": None,
            "first_pay_dt": "2026-03-03",
            "other_dt_b": "2026-03-04",
            "other_dt_a": "2026-03-05",
            "non_date_col": "hello"
        },
        {
            "borrower_id": "B4",
            "loan_amount": 4000.0,
            "disb_dt": None,
            "app_date": None,
            "first_pay_dt": None,
            "other_dt_b": "2026-04-04",
            "other_dt_a": "2026-04-05",
            "non_date_col": "hello"
        },
        {
            "borrower_id": "B5",
            "loan_amount": 5000.0,
            "disb_dt": None,
            "app_date": None,
            "first_pay_dt": None,
            "other_dt_b": None,
            "other_dt_a": None,
            "non_date_col": "hello"
        }
    ])

    # Run canonical transformation
    raw_cnt, b_cnt, loan_cnt = await transform_and_populate(db, dataset_id, version_id, df)
    assert raw_cnt == 5

    # Query loans and assert dates / synthetic flag
    loans_res = await db.execute(
        select(Loan).where(Loan.dataset_id == dataset_id).order_by(Loan.loan_amount)
    )
    loans = loans_res.scalars().all()
    assert len(loans) == 5

    # Row 0: Uses disb_dt (2026-01-01)
    assert loans[0].disbursement_date == date(2026, 1, 1)
    assert loans[0].additional_attributes_json is not None
    assert loans[0].additional_attributes_json.get("date_is_synthetic") is False

    # Row 1: Uses app_date (2026-02-02)
    assert loans[1].disbursement_date == date(2026, 2, 2)
    assert loans[1].additional_attributes_json is not None
    assert loans[1].additional_attributes_json.get("date_is_synthetic") is False

    # Row 2: Uses first_pay_dt (2026-03-03)
    assert loans[2].disbursement_date == date(2026, 3, 3)
    assert loans[2].additional_attributes_json is not None
    assert loans[2].additional_attributes_json.get("date_is_synthetic") is False

    # Row 3: Uses other_dt_a alphabetically (2026-04-05)
    assert loans[3].disbursement_date == date(2026, 4, 5)
    assert loans[3].additional_attributes_json is not None
    assert loans[3].additional_attributes_json.get("date_is_synthetic") is False

    # Row 4: No date available. Sets canonical date as None and flag as True.
    assert loans[4].disbursement_date is None
    assert loans[4].additional_attributes_json is not None
    assert loans[4].additional_attributes_json.get("date_is_synthetic") is True

    # Assert that RawRecord's canonical_data_json also has the flags
    raw_records_res = await db.execute(
        select(RawRecord).where(RawRecord.dataset_id == dataset_id).order_by(RawRecord.source_row_number)
    )
    raw_records = raw_records_res.scalars().all()
    assert len(raw_records) == 5

    assert raw_records[0].canonical_data_json.get("date_is_synthetic") is False
    assert raw_records[1].canonical_data_json.get("date_is_synthetic") is False
    assert raw_records[2].canonical_data_json.get("date_is_synthetic") is False
    assert raw_records[3].canonical_data_json.get("date_is_synthetic") is False
    assert raw_records[4].canonical_data_json.get("date_is_synthetic") is True
