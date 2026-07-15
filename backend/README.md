# RiskLens Backend API

The backend is built with FastAPI, using SQLAlchemy for asynchronous ORM database interactions and Alembic for schema migrations.

---

## Technical Stack
- **FastAPI**: Modern, high-performance web framework.
- **SQLAlchemy (Async)**: Async engine mapping using `asyncpg` (PostgreSQL) and `aiosqlite` (SQLite test environment).
- **Alembic**: Database migrations management.
- **SlowAPI**: Rate limiting library based on limits.
- **Pytest + AnyIO**: Testing framework for asynchronous endpoint calls.

---

## Local Development Setup

### 1. Environment Setup
1. Create and activate a Python virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy and customize the `.env` template from the root workspace directory.

### 2. Database Migrations & Seeds
To initialize the Postgres database schema and insert basic seed records (static roles, default admin user, and system config settings):
```bash
alembic upgrade head
python app/seed/run_seed.py
```

### 3. Running the Server
Launch the FastAPI uvicorn hot-reloader:
```bash
uvicorn app.main:app --reload --port 8000
```
API interactive swagger docs are available at `http://localhost:8000/docs`.

---

## Running Backend Tests

The backend includes a comprehensive pytest suite executing async calls against an isolated SQLite test database:
```bash
python -m pytest
```

---

## Code Quality & Linting

Before pushing changes, run the code quality checks to ensure compliance:

### 1. Ruff Linting
Check for unused imports, syntax formatting, and standard rules:
```bash
ruff check .
```

### 2. Black Formatting
Verify that python code complies with default black format constraints:
```bash
black --check .
```
To auto-format the codebase:
```bash
black .
```

### 3. Mypy Type Checking
Run strict static typing checks:
```bash
mypy app
```
Ensure all critical methods and endpoints contain strict type-annotations.
