import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.public_dataset_source import PublicDatasetSource


async def seed_public_dataset_sources(db: AsyncSession) -> None:
    """Idempotently seeds standard curated external credit reference datasets catalogue."""
    sources_data = [
        {
            "name": "Home Credit Default Risk",
            "provider": "Kaggle",
            "source_url": "https://www.kaggle.com/c/home-credit-default-risk",
            "dataset_category": "Consumer Credit",
            "access_type": "FREE",
            "recommended_use": "Primary consumer credit-risk analytics demo dataset. Good for borrower, loan, income, employment, repayment burden, and historical default flag mapping.",
            "notes": "Requires Kaggle registration to download raw dataset files.",
        },
        {
            "name": "Credit Risk Dataset",
            "provider": "Kaggle",
            "source_url": "https://www.kaggle.com/datasets/laotse/credit-risk-dataset",
            "dataset_category": "Consumer Credit",
            "access_type": "FREE",
            "recommended_use": "Clean borrower-level credit-risk analytics dataset. Good for quick demo workflows and deterministic rule-based scoring.",
            "notes": "Excellent for validation and profiling testing.",
        },
        {
            "name": "Lending Club Loan Data",
            "provider": "Kaggle",
            "source_url": "https://www.kaggle.com/datasets/wordsforthewise/lending-club",
            "dataset_category": "Peer-to-Peer Loans",
            "access_type": "FREE",
            "recommended_use": "Loan status, grades, interest rates, borrower attributes, portfolio analysis.",
            "notes": "Very large dataset. Do not bundle in application codebase repository.",
        },
        {
            "name": "Default of Credit Card Clients",
            "provider": "UCI Machine Learning Repository",
            "source_url": "https://archive.ics.uci.edu/dataset/350/default+of+credit+card+clients",
            "dataset_category": "Credit Cards",
            "access_type": "FREE",
            "recommended_use": "Credit card repayment behavior, limits, bill amounts, previous payments.",
            "notes": "Use only for descriptive and diagnostic analytics, not ML.",
        },
        {
            "name": "CFPB Consumer Credit Trends",
            "provider": "Consumer Financial Protection Bureau",
            "source_url": "https://www.consumerfinance.gov/data-research/consumer-credit-trends/",
            "dataset_category": "Market Trends",
            "access_type": "FREE",
            "recommended_use": "Market-level consumer credit benchmarking. Useful for external reference dashboards and trend comparison.",
            "notes": "Sourced from credit database panels.",
        },
        {
            "name": "CFPB HMDA Mortgage Data",
            "provider": "Consumer Financial Protection Bureau / FFIEC",
            "source_url": "https://www.consumerfinance.gov/data-research/hmda/",
            "dataset_category": "Mortgages",
            "access_type": "FREE",
            "recommended_use": "Mortgage loan-level public data, fair-lending and regional lending pattern analysis.",
            "notes": "Public disclosures are privacy-modified.",
        },
        {
            "name": "Fannie Mae Single-Family Loan Performance Data",
            "provider": "Fannie Mae",
            "source_url": "https://www.fanniemae.com/portal/funding-the-market/data/loan-performance-data.html",
            "dataset_category": "Mortgages",
            "access_type": "LICENSED",
            "recommended_use": "Mortgage credit performance, acquisition/performance data.",
            "notes": "Requires registration and terms acceptance.",
        },
        {
            "name": "Freddie Mac Single-Family Loan-Level Dataset",
            "provider": "Freddie Mac",
            "source_url": "https://www.freddiemac.com/research/datasets/sf-loanlevel-dataset",
            "dataset_category": "Mortgages",
            "access_type": "LICENSED",
            "recommended_use": "Mortgage performance, credit performance, prepayment, foreclosure alternatives.",
            "notes": "Requires registration/sign-in and terms acceptance.",
        },
        {
            "name": "Federal Reserve Survey of Consumer Finances",
            "provider": "Federal Reserve Board",
            "source_url": "https://www.federalreserve.gov/econres/scfindex.htm",
            "dataset_category": "Macroeconomic Survey",
            "access_type": "FREE",
            "recommended_use": "Household balance sheet, debt, income, demographic benchmark analytics.",
            "notes": "Better for macro/household benchmark analytics than borrower-level loan analytics.",
        },
        {
            "name": "FDIC Quarterly Banking Profile",
            "provider": "FDIC",
            "source_url": "https://www.fdic.gov/quarterly-banking-profile",
            "dataset_category": "Banking Industry Profile",
            "access_type": "FREE",
            "recommended_use": "Banking industry benchmark metrics, asset quality, earnings, loan/deposit activity.",
            "notes": "Institution/industry-level analytics, not borrower-level data.",
        },
        {
            "name": "World Bank Global Findex",
            "provider": "World Bank",
            "source_url": "https://microdata.worldbank.org/index.php/catalog/global-findex",
            "dataset_category": "Macro Financial Inclusion",
            "access_type": "FREE",
            "recommended_use": "Financial inclusion, saving, borrowing, payments, risk management across economies.",
            "notes": "Macro/financial-inclusion benchmarking.",
        },
    ]

    for sdata in sources_data:
        stmt = select(PublicDatasetSource).where(PublicDatasetSource.name == sdata["name"])
        res = await db.execute(stmt)
        existing_source = res.scalar_one_or_none()

        if not existing_source:
            source = PublicDatasetSource(
                id=uuid.uuid4(),
                name=sdata["name"],
                provider=sdata["provider"],
                source_url=sdata["source_url"],
                dataset_category=sdata["dataset_category"],
                access_type=sdata["access_type"],
                recommended_use=sdata["recommended_use"],
                notes=sdata["notes"],
                is_active=True,
            )
            db.add(source)
            print(f"Dataset source seeded: {sdata['name']}")
        else:
            # Sync metadata changes
            existing_source.provider = sdata["provider"]
            existing_source.source_url = sdata["source_url"]
            existing_source.dataset_category = sdata["dataset_category"]
            existing_source.access_type = sdata["access_type"]
            existing_source.recommended_use = sdata["recommended_use"]
            existing_source.notes = sdata["notes"]
            print(f"Dataset source verified: {sdata['name']}")

    await db.flush()
