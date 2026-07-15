# RiskLens Architecture Design Specification

This document details the software architecture, component relations, data flows, and design patterns of the RiskLens Analytics platform.

---

## 1. Component Topology

The system uses a decoupled client-server architecture:
1. **React Client (SPA)**: Serves the dashboard interfaces, handles authenticated session contexts, and interacts with backend routers via Axios.
2. **FastAPI Server (REST)**: Enforces RBAC roles, rate-limiting, and triggers analytical calculations or report assemblies.
3. **Relational Database**: PostgreSQL stores persistent dataset listings, mappings, raw records, validation errors, and report files.

```text
+-------------------+      REST API HTTP Requests      +-------------------+
|                   |=================================>|                   |
|   React SPA       |                                  |   FastAPI Server  |
|  (Frontend Client)|<=================================|     (Backend)     |
|                   |      JSON Envelopes / Binaries   |                   |
+-------------------+                                  +---------+---------+
                                                                 |
                                                           SQL queries (Async)
                                                                 |
                                                                 v
                                                       +-------------------+
                                                       |    PostgreSQL     |
                                                       |     (Database)    |
                                                       +-------------------+
```

---

## 2. Ingestion & Mappings Pipeline

The platform ingests files and transforms raw rows into canonical loan performance models through a structured, multi-step pipeline:

```text
[ Upload File ] -> [ Save Raw Records ] -> [ Infer Schema ]
                                                  |
                                                  v
[ Save Canonical Records ] <- [ Map Canonical Fields ]
```

1. **Upload**: User uploads a CSV, XLSX, or JSON file.
2. **Raw Ingestion**: The system writes raw data to `RawRecord` lines and saves column structures to `DatasetColumn`.
3. **Schema Inference**: The `SchemaInferer` analyzes raw types and recommends canonical mappings.
4. **Canonical Mapping**: Users match raw columns tocanonical fields (e.g. `borrower_id`, `income`, `loan_amount`, `loan_purpose`).
5. **Quality Validation**: The quality engine runs checks for missing values, duplicates, and invalid datatypes, recording results to `ValidationIssue` structures.

---

## 3. Analytics & Profiling Engines

Calculations are driven by dedicated, deterministic engines:
- **DataQualityEngine**: Compiles statistical counts of formatting/mapping issues, missing required elements, and duplicate records.
- **ProfilingEngine**: Computes statistical summaries (means, medians, standard deviations, percentiles) and outlier bounds (IQR & Z-score) for numerical columns, and value-frequencies for categorical fields.
- **CreditRiskEngine**: Computes borrower exposure bands and loans delinquency age buckets.
- **TrendEngine**: Groups metrics chronologically by disbursement month to generate historical trend matrices.
- **VintageEngine**: Evaluates performance cohorts by origination quarter.
- **MigrationEngine**: Compares credit ratings transitions between sequential version runs.

---

## 4. API Layer & Security Lifecycle

- **JSON Envelopes**: All API responses use the strict generic format:
  ```json
  {
    "success": true,
    "message": "Description",
    "data": { ... },
    "error": null,
    "meta": { "timestamp": "...", "request_id": "..." }
  }
  ```
- **Session Authentication**: JWT access tokens are signed with symmetric HS256 keys. Refresh tokens are stored in the client's local storage and exchanged automatically when access tokens expire.
- **Rate-Limiting**: Enforced on critical endpoints (login, uploads, AI calls) using `SlowAPI` with client IP address keys.
