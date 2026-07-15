import uuid
import pytest
from sqlalchemy import select
from app.models.dataset import Dataset
from app.models.dataset_version import DatasetVersion
from app.models.borrower import Borrower
from app.models.loan import Loan
from app.models.risk_assessment import RiskAssessment
from app.models.user import User
from app.enums.dataset_status import DatasetStatusEnum
from app.enums.validation_status import ValidationStatusEnum
from app.enums.risk_category import RiskCategoryEnum
from app.services.analytics.exposure_calculation_service import ExposureCalculationService

@pytest.mark.anyio
async def test_exposure_calculation_service(db):
    admin_user = (await db.execute(select(User).where(User.email == "admin@risklens.com"))).scalar_one()

    # 1. Setup dataset and version
    dataset_id = uuid.uuid4()
    version_id = uuid.uuid4()
    
    dataset = Dataset(
        id=dataset_id,
        name="Exposure Service Test Dataset",
        file_type="CSV",
        original_file_name="exposure_test.csv",
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
        row_count=3,
        column_count=5
    )
    db.add(version)
    await db.commit()

    # 2. Add borrowers, loans, and assessments
    # Loan 1: Outstanding = 100000.0, Region = "North", Category = "HIGH", Status = "Active"
    # Loan 2: Outstanding = 200000.0, Region = "South", Category = "LOW", Status = "Active"
    # Loan 3: Outstanding = None (Null), Region = "North", Category = "LOW", Status = "Closed"
    b1_id = uuid.uuid4()
    b2_id = uuid.uuid4()
    b3_id = uuid.uuid4()
    
    b1 = Borrower(id=b1_id, dataset_id=dataset_id, version_id=version_id, source_borrower_id="B1", region="North")
    b2 = Borrower(id=b2_id, dataset_id=dataset_id, version_id=version_id, source_borrower_id="B2", region="South")
    b3 = Borrower(id=b3_id, dataset_id=dataset_id, version_id=version_id, source_borrower_id="B3", region="North")
    db.add_all([b1, b2, b3])

    l1_id = uuid.uuid4()
    l2_id = uuid.uuid4()
    l3_id = uuid.uuid4()

    l1 = Loan(
        id=l1_id, dataset_id=dataset_id, version_id=version_id, borrower_id=b1_id,
        outstanding_amount=100000.0, loan_status="Active", loan_purpose="Business", delinquency_days=45
    )
    l2 = Loan(
        id=l2_id, dataset_id=dataset_id, version_id=version_id, borrower_id=b2_id,
        outstanding_amount=200000.0, loan_status="Active", loan_purpose="Business", delinquency_days=15
    )
    l3 = Loan(
        id=l3_id, dataset_id=dataset_id, version_id=version_id, borrower_id=b3_id,
        outstanding_amount=None, loan_status="Closed", loan_purpose="Personal", delinquency_days=0
    )
    db.add_all([l1, l2, l3])

    ra1 = RiskAssessment(id=uuid.uuid4(), dataset_id=dataset_id, version_id=version_id, loan_id=l1_id, risk_score=85.0, risk_category=RiskCategoryEnum.HIGH)
    ra2 = RiskAssessment(id=uuid.uuid4(), dataset_id=dataset_id, version_id=version_id, loan_id=l2_id, risk_score=15.0, risk_category=RiskCategoryEnum.LOW)
    ra3 = RiskAssessment(id=uuid.uuid4(), dataset_id=dataset_id, version_id=version_id, loan_id=l3_id, risk_score=10.0, risk_category=RiskCategoryEnum.LOW)
    db.add_all([ra1, ra2, ra3])
    
    await db.commit()

    # Instantiate ExposureCalculationService
    service = ExposureCalculationService(db)

    # 1. Verify total exposure without filters
    tot = await service.calculate_total_exposure(dataset_id)
    assert tot == 300000.0

    # 2. Verify total exposure with Loan filter
    tot_filtered = await service.calculate_total_exposure(dataset_id, filters={"loan_status": "Active"})
    assert tot_filtered == 300000.0

    # 3. Verify total exposure with Borrower filter
    tot_region = await service.calculate_total_exposure(dataset_id, filters={"region": "North"})
    assert tot_region == 100000.0 # 100k + null (0.0) = 100k

    # 4. Verify total exposure with Risk category filter
    tot_high = await service.calculate_total_exposure(dataset_id, filters={"risk_category": RiskCategoryEnum.HIGH})
    assert tot_high == 100000.0

    # 5. Verify dimension exposure: region
    exp_region = await service.calculate_exposure_by_dimension(dataset_id, "region")
    assert exp_region.get("North") == 100000.0
    assert exp_region.get("South") == 200000.0

    # 6. Verify dimension exposure: loan_status
    exp_status = await service.calculate_exposure_by_dimension(dataset_id, "loan_status")
    assert exp_status.get("Active") == 300000.0
    assert exp_status.get("Closed") == 0.0

    # 7. Verify dimension exposure: risk_category
    exp_risk = await service.calculate_exposure_by_dimension(dataset_id, "risk_category")
    assert exp_risk.get("HIGH") == 100000.0
    assert exp_risk.get("LOW") == 200000.0

    # 8. Verify operator filter for delinquency_days > 30
    tot_delinq = await service.calculate_total_exposure(dataset_id, filters={"delinquency_days": ("gt", 30)})
    assert tot_delinq == 100000.0
