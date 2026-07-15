# RiskLens Analytics Catalog

This catalog documents the statistical calculations and deterministic formulas used by the RiskLens analytical engines.

---

## 1. Borrower Risk Analytics

Analyzes borrower traits and clusters default rates across demographics:
- **Age Cohorts**: Borrower loan applications are categorized into age bands:
  - `Under 25`
  - `25 - 34`
  - `35 - 44`
  - `45 - 54`
  - `55 - 64`
  - `65 and Over`
- **Employment and Income Slices**: Computes average income, average debt-to-income (DTI) ratio, and default occurrences grouped by `employment_type`.

---

## 2. Loan Exposure Analytics

Provides portfolio stress indicators:
- **Delinquency Ageing (DPD) Buckets**: Evaluates days-past-due parameters to distribute outstanding balances across aging buckets:
  - `Current` (0 DPD)
  - `1 - 30 Days`
  - `31 - 60 Days`
  - `61 - 90 Days`
  - `90+ Days` (Non-Performing Loans / Default)
- **Exposure Waterfall**: Computes active exposure metrics:
  - `Total Principal Disbursed`
  - `Active Outstanding Principal`
  - `Total Delinquent Balance`
  - `Delinquency Ratio` (`Total Delinquent Balance` / `Active Outstanding Principal`)

---

## 3. Concentration Analysis (HHI)

Measures risk concentration across portfolio dimensions (geography, loan grade, or industry sector) using the **Herfindahl-Hirschman Index (HHI)**:

$$\text{HHI} = \sum_{i=1}^{N} (s_i)^2$$

Where $s_i$ is the percentage share of exposure for segment $i$ (expressed as a whole number, e.g. 20% is 20).
- **HHI Interpretation**:
  - `HHI < 1500`: Unconcentrated (Low Risk)
  - `1500 <= HHI <= 2500`: Moderate Concentration
  - `HHI > 2500`: High Concentration (Elevated risk exposure)

---

## 4. Historical Trend Analysis

Aggregates loan properties chronologically by their `disbursement_date` month (`YYYY-MM` format):
- **Growth Trends**: Monthly count and volume of disbursed loans.
- **Exposure Trends**: Active monthly outstanding principal and high-risk segment outstanding principal.
- **Risk Trends**: Monthly averages of computed credit risk scores and delinquency age metrics.

---

## 5. Cohorted Vintage Analysis

Tracks credit performance cohorts grouped by the calendar quarter of loan disbursement (e.g. `2024-Q1`, `2024-Q2`):
- **Periods on Book (POB)**: Track metrics (like write-offs or delinquency rates) sequentially at 3, 6, 9, 12, 18, and 24 months post-disbursement.
- **Cohort Matrix**: Evaluates cohort deterioration patterns over time to pinpoint changes in underwriting standards.

---

## 6. Credit Risk Rating Migration

Computes rating transition matrices between consecutive dataset versions (e.g. comparing V1 to V2 updates):
- **Transition Count Matrix**: Traces migration counts (e.g., number of borrowers who migrated from rating `LOW` to `HIGH` risk).
- **Exposure Transition Matrix**: Measures value change balances moving between risk categories.
