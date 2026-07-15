.PHONY: install setup-env backend-dev frontend-dev docker-up docker-down test lint clean

# Default action
all: install

# Install dependencies for both backend and frontend
install:
	cd backend && pip install -r requirements.txt
	cd frontend && npm install

# Setup environment file from example
setup-env:
	cp .env.example .env

# Start local backend development server
backend-dev:
	cd backend && uvicorn app.main:app --reload --port 8000

# Start local frontend development server
frontend-dev:
	cd frontend && npm run dev

# Boot entire Docker Compose stack
docker-up:
	docker compose up --build

# Tear down Docker Compose stack
docker-down:
	docker compose down -v

# Run both backend and frontend tests
test:
	cd backend && python -m pytest
	cd frontend && npm test

# Run quality checks (Ruff, Black, Mypy, and Frontend build checks)
lint:
	cd backend && ruff check .
	cd backend && black --check .
	cd backend && mypy app
	cd frontend && npm run build

# Clean caching and temporary database files
clean:
	rm -rf backend/.pytest_cache
	rm -rf backend/.mypy_cache
	rm -f backend/test_risklens.db
