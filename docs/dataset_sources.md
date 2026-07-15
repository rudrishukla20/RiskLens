# RiskLens Analytics Public Dataset Sources Catalogue

This document outlines the standard curated catalog of public credit-risk, macroeconomic benchmarking, and mortgage loan-performance datasets integrated into the RiskLens platform.

---

## Catalogued Datasets

### 1. Home Credit Default Risk
- **Provider**: Kaggle
- **URL**: [c/home-credit-default-risk](https://www.kaggle.com/c/home-credit-default-risk)
- **Use Case**: Primary consumer credit-risk analytics demo dataset.
- **Notes**: Excellent for testing borrower demographic mapping, loan properties, income verification, repayment burden ratios, and historical default flags.
- **Access Rule**: Requires Kaggle account credentials for API download.

### 2. Credit Risk Dataset
- **Provider**: Kaggle
- **URL**: [laotse/credit-risk-dataset](https://www.kaggle.com/datasets/laotse/credit-risk-dataset)
- **Use Case**: Clean borrower-level credit-risk analytics dataset.
- **Notes**: Ideal for quick onboarding, workflow demonstrations, and verifying deterministic rule-based credit scoring engines.
- **Access Rule**: Requires Kaggle account credentials for API download.

### 3. Lending Club Loan Data
- **Provider**: Kaggle
- **URL**: [datasets/wordsforthewise/lending-club](https://www.kaggle.com/datasets/wordsforthewise/lending-club)
- **Use Case**: Testing cohorted loan status, default curves, grading, interest rates, and loan-to-income attributes.
- **Notes**: Large file dataset. **Do not bundle inside this repository.** Sourced via external URL link mappings.
- **Access Rule**: Requires Kaggle registration.

### 4. Default of Credit Card Clients
- **Provider**: UCI Machine Learning Repository
- **URL**: [default+of+credit+card+clients](https://archive.ics.uci.edu/dataset/350/default+of+credit+card+clients)
- **Use Case**: Credit card repayment behavior, credit limits, billing details, and historical payments.
- **Notes**: Restricted to descriptive statistics and diagnostic analytics. **No ML/DL models allowed.**

### 5. CFPB Consumer Credit Trends
- **Provider**: Consumer Financial Protection Bureau
- **URL**: [consumer-credit-trends](https://www.consumerfinance.gov/data-research/consumer-credit-trends/)
- **Use Case**: Macro/market-level consumer credit benchmarking.
- **Notes**: Ideal for building benchmark comparison tiles on active risk dashboards.

### 6. CFPB HMDA Mortgage Data
- **Provider**: Consumer Financial Protection Bureau / FFIEC
- **URL**: [hmda](https://www.consumerfinance.gov/data-research/hmda/)
- **Use Case**: Mortgage loan-level public data, fair-lending assessment, and regional patterns concentration analysis.
- **Notes**: Public dataset containing privacy-modified data boundaries.

### 7. Fannie Mae Single-Family Loan Performance Data
- **Provider**: Fannie Mae
- **URL**: [loan-performance-data.html](https://www.fanniemae.com/portal/funding-the-market/data/loan-performance-data.html)
- **Use Case**: Mortgage credit performance and long-term vintage acquisition analytics.
- **Notes**: **Strictly requires registration, terms acceptance, and licensing sign-in.** No auto-scrapers allowed.

### 8. Freddie Mac Single-Family Loan-Level Dataset
- **Provider**: Freddie Mac
- **URL**: [sf-loanlevel-dataset](https://www.freddiemac.com/research/datasets/sf-loanlevel-dataset)
- **Use Case**: Mortgage performance tracking, prepayment risks, and foreclosure alternatives benchmarks.
- **Notes**: **Strictly requires user registration, sign-in, and terms acceptance.**

### 9. Federal Reserve Survey of Consumer Finances
- **Provider**: Federal Reserve Board
- **URL**: [scfindex.htm](https://www.federalreserve.gov/econres/scfindex.htm)
- **Use Case**: Household balance sheets, consumer debt burdens, and demographic benchmark analytics.
- **Notes**: Primarily utilized for macro-econometric household dashboards, not individual borrower scoring.

### 10. FDIC Quarterly Banking Profile
- **Provider**: FDIC
- **URL**: [quarterly-banking-profile](https://www.fdic.gov/quarterly-banking-profile)
- **Use Case**: Banking industry benchmark metrics, asset quality reviews, net interest margins, and institutional loan allocations.
- **Notes**: Restricted to institution/industry-level trend charts.

### 11. World Bank Global Findex
- **Provider**: World Bank
- **URL**: [global-findex](https://microdata.worldbank.org/index.php/catalog/global-findex)
- **Use Case**: Financial inclusion, savings rates, credit usage, and payments methods benchmarking across global economies.
- **Notes**: Focuses on macro-level developmental benchmarking.

---

## Local Development Policy

1. **Auto-Download Pipeline**: The platform does **not** scrape or auto-download files from external providers to respect terms of service.
2. **Local Fixtures**: For unit testing and local workflow checks, refer to the small mock fixtures located under:
   - `backend/tests/fixtures/sample_credit_dataset.csv`
