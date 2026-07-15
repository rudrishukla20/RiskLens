import uuid

import pytest

from app.analytics.profiling_engine import ProfilingEngine
from app.enums.dataset_status import DatasetStatusEnum
from app.enums.validation_status import ValidationStatusEnum
from app.models.dataset import Dataset
from app.models.dataset_version import DatasetVersion
from app.models.raw_record import RawRecord


@pytest.mark.anyio
async def test_data_profiling_engine(client, db, admin_headers):
    from sqlalchemy import select

    from app.models.user import User

    admin_user = (await db.execute(select(User).where(User.email == "admin@risklens.com"))).scalar_one()

    # 1. Create a dummy dataset in db
    dataset_id = uuid.uuid4()
    version_id = uuid.uuid4()

    dataset = Dataset(
        id=dataset_id,
        name="Profiling Test Dataset",
        file_type="CSV",
        original_file_name="profiling_test.csv",
        uploaded_by=admin_user.id,
        upload_status=DatasetStatusEnum.UPLOADED,
        validation_status=ValidationStatusEnum.PENDING,
        active_version_id=version_id,
    )
    db.add(dataset)

    version = DatasetVersion(id=version_id, dataset_id=dataset_id, version_number=1, row_count=5, column_count=3)
    db.add(version)

    # 2. Add RawRecords with:
    # - Numeric column: "age" (with values: 25, 30, 35, 40, 150 -> 150 is outlier)
    # - Categorical column: "employment" (with values: "Full-time", "Part-time", "Full-time", "Unemployed", "Full-time")
    records_data = [
        {"age": 25, "employment": "Full-time"},
        {"age": 30, "employment": "Part-time"},
        {"age": 35, "employment": "Full-time"},
        {"age": 40, "employment": "Unemployed"},
        {"age": 150, "employment": "Full-time"},  # 150 is outlier
    ]
    for idx, r in enumerate(records_data):
        rr = RawRecord(
            id=uuid.uuid4(),
            dataset_id=dataset_id,
            version_id=version_id,
            source_row_number=idx + 1,
            raw_data_json=r,
            canonical_data_json=r,
        )
        db.add(rr)

    await db.commit()

    # 3. Trigger profiling engine directly
    profiler = ProfilingEngine(db)
    await profiler.run_profiling(dataset_id, version_id)
    await db.commit()

    db.expire_all()
    # 4. Get latest profiling run summary via API
    res_latest = await client.get(f"/api/v1/datasets/{dataset_id}/profile/latest", headers=admin_headers)
    assert res_latest.status_code == 200
    latest_data = res_latest.json()
    assert latest_data["success"] is True
    assert latest_data["data"]["row_count"] == 5
    assert latest_data["data"]["status"] == "ANALYZED"

    # 5. Query column profiles via API
    res_cols = await client.get(f"/api/v1/datasets/{dataset_id}/profile/columns", headers=admin_headers)
    assert res_cols.status_code == 200
    cols_data = res_cols.json()
    assert cols_data["success"] is True
    assert len(cols_data["data"]) == 2

    # Verify column statistics
    age_profile = next(c for c in cols_data["data"] if c["column_name"] == "age")
    employment_profile = next(c for c in cols_data["data"] if c["column_name"] == "employment")

    # Numeric profile checks
    assert age_profile["data_type"].upper() in ("NUMERIC", "INTEGER")
    assert age_profile["mean_value"] == 56.0
    assert age_profile["min_value"] == 25.0
    assert age_profile["max_value"] == 150.0

    # Categorical profile checks
    assert employment_profile["data_type"].upper() in ("CATEGORICAL", "STRING")
    assert employment_profile["unique_count"] == 3
    # Check frequency count structure
    freqs = employment_profile["distribution"]
    assert freqs["type"] == "categorical"
    cat_counts = dict(zip(freqs["categories"], freqs["counts"]))
    assert cat_counts["Full-time"] == 3
    assert cat_counts["Part-time"] == 1
    assert cat_counts["Unemployed"] == 1
