# RiskLens Analytics

RiskLens Analytics is an enterprise-grade credit risk dashboard and portfolio monitoring application. It enables risk officers and administrators to register datasets, validate schemas, profile loan portfolios, evaluate credit risk exposure segments, and export structured compliance reports with optional AI summaries.

---

## Final Role Model

The application enforces a strict, two-tier Role-Based Access Control (RBAC) schema. The roles are:
- **ADMIN**: Access to administrative routes, system overview, user provisioning, system settings, audit logs, and dataset registries.
- **CREDIT_RISK_GOVERNANCE_OFFICER**: Access to credit-risk dashboards, data catalogs, borrower demographics, loan ageing, portfolio metrics, concentration indices, compliance documents, AI commentary, and reports compilation.

*Note: Role management features (like creating, updating, or deleting roles) are not supported by the platform. Roles are seeded statically during initialization.*

---

## Core Technologies

- **Backend**: FastAPI (Python), SQLAlchemy (async ORM), PostgreSQL (Production), SQLite/aiosqlite (Testing), Alembic (migrations), SlowAPI (rate-limiting).
- **Frontend**: React, TypeScript, Vite, TailwindCSS, TanStack React Query, Lucide Icons, Recharts (visualizations).
- **Infrastructure**: Docker, Docker Compose, PostgreSQL 18.4 database.

---

## Directory Structure

```text
RiskLens/
├── backend/                  # FastAPI Application Code
│   ├── app/                  # Application core, models, schemas, routers, services, analytics engines
│   ├── alembic/              # Database migration scripts
│   ├── tests/                # Pytest suites
│   ├── Dockerfile            # Container build context
│   └── requirements.txt      # Python dependencies
├── frontend/                 # React Application Code
│   ├── src/                  # App components, pages, hooks, services, routing
│   ├── tests/                # Vitest & React Testing Library suites
│   └── Dockerfile            # Container build context
├── docs/                     # Comprehensive architecture and user guides
├── scripts/                  # Shell scripts for container boot sequencing
├── docker-compose.yml        # Multi-service stack orchestration template
└── Makefile                  # Command shortcuts
```

---

## System Architecture

```text
  +--------------------------------------------------------------+
  |                        React Frontend                        |
  |             (TypeScript + Vite + Recharts + Tailwind)        |
  +------------------------------+-------------------------------+
                                 |
                          REST API Requests (Axios Client)
                                 |
                                 v
  +--------------------------------------------------------------+
  |                        FastAPI Backend                       |
  |   +------------------------------------------------------+   |
  |   |                API Routers & Guards                  |   |
  |   +--------------------------+---------------------------+   |
  |                              |                               |
  |                              v                               |
  |   +------------------------------------------------------+   |
  |   |           Services & Analytical Engines              |   |
  |   |   - Borrower Analytics       - Concentration (HHI)   |   |
  |   |   - Loan Exposure            - Trend & Vintage       |   |
  |   |   - Profiling Engine         - Data Quality (DQ)     |   |
  |   +--------------------------+---------------------------+   |
  |                              |                               |
  |                              v                               |
  |   +------------------------------------------------------+   |
  |   |                 SQLAlchemy Async ORM                 |   |
  |   +------------------------------------------------------+   |
  +------------------------------+-------------------------------+
                                 |
                   Async DB Connection (asyncpg / aiosqlite)
                                 |
                                 v
  +--------------------------------------------------------------+
  |                           Databases                          |
  |        - PostgreSQL (Prod)      - SQLite (Unit Tests)        |
  +--------------------------------------------------------------+
```

---

## Environment Configuration

A single `.env` file at the root coordinates settings across backend, frontend, and database services:

```env
APP_ENV=local
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/risklens
TEST_DATABASE_URL=sqlite+aiosqlite:///test_risklens.db
JWT_SECRET_KEY=yoursupersecurejwtsecretkeyherechangeit
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# AI LLM Provider Configuration (disabled / openai / anthropic)
AI_PROVIDER=disabled
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
AI_MODEL_NAME=
```

---

## Boot Instructions

### 1. Running with Docker Compose (Recommended)

To bring up the entire PostgreSQL, FastAPI backend, and React frontend stack:
```bash
docker compose up --build -d
```
The services will be available at:
- **Frontend**: `http://localhost:5173`
- **Backend API**: `http://localhost:8000`
- **PostgreSQL**: port `5432`

To stop and remove containers and volumes:
```bash
docker compose down -v
```

### 2. Running Locally for Development

#### Backend Local Setup:
1. Navigate to `backend/`.
2. Create and activate a Python virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run migrations and database seeds:
   ```bash
   alembic upgrade head
   python app/seed/run_seed.py
   ```
5. Launch the FastAPI server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

#### Frontend Local Setup:
1. Navigate to `frontend/`.
2. Install Node dependencies:
   ```bash
   npm install
   ```
3. Run the development server:
   ```bash
   npm run dev
   ```

---

## Database Migrations & Seeding

- **Run migrations**: `alembic upgrade head`
- **Create new migration**: `alembic revision --autogenerate -m "description"`
- **Seed database**: `python app/seed/run_seed.py` (idempotent; seeds static roles, default admin user, and system variables).

---

## Verification & Testing

### Running Backend Tests (Pytest)
From the `backend/` directory:
```bash
pytest
```

### Running Frontend Tests (Vitest)
From the `frontend/` directory:
```bash
npm run test
```

### Formatting & Code Quality
- **Backend format check**: `black --check .`
- **Backend lint check**: `ruff check .`
- **Backend type check**: `mypy app`
- **Frontend build/typecheck**: `npm run build`

---

## Key Workflows

### 1. Dataset Upload & Mapping Workflow
1. Users upload a raw credit dataset (CSV, Excel, or JSON format).
2. The platform performs schema inference to determine datatypes and detect column names.
3. The user confirms mappings of the inferred fields into RiskLens canonical definitions (e.g. `borrower_id`, `income`, `loan_amount`, `loan_purpose`).
4. The system validates raw records, records validation issues (missing values, duplicates, invalid datatypes), and triggers profiling metrics.

### 2. Analytical Calculations & Report Workflow
1. Once a dataset mapping is confirmed, a validation run compiles and stores validation scores.
2. The profiling engine executes statistical summaries, histograms, and outlier evaluations on numeric and categorical dimensions.
3. Credit risk analytics engines compute DPD delinquency aging buckets, borrower band segments risk ratios, and HHI concentration indexes.
4. Users trigger PDF, Excel (XLSX), or CSV reports compile outputs, which are written to storage and available for download.

### 3. AI Commentary Behavior
- **Enabled**: When `AI_PROVIDER` is set to `openai` or `anthropic` with valid keys, the system executes an LLM chat completion request grounded on database-computed metrics, storing structured qualitative summaries, finding lists, and risk observations.
- **Disabled**: If `AI_PROVIDER` is unset or set to `disabled`, the system returns a standard fallback stating that AI commentary is disabled and prompts configurations checklist guidance.

---

## Assumptions & Breaking Changes

- **Testing Database Fallback**: Async SQLite (`sqlite+aiosqlite`) is utilized for tests. `Base.metadata.create_all` compiles custom `JSONB` to `JSON` columns automatically via custom dialect overrides.
- **Breaking Changes from Legacy Version**:
  - Replaced legacy password requirements with strict security policies (minimum 12 characters, requiring uppercase, lowercase, numbers, and special characters).
  - The custom response schema `{ success: boolean, message: string, data: Any, error: Any, meta: Any }` is enforced globally across all API routes.
