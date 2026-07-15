# RiskLens Deployment & Operations Guide

This document outlines the infrastructure, environment setups, and container management procedures for deploying the RiskLens platform.

---

## 1. Local / Staging Docker Stack

The production-ready container stack is orchestrated using `docker-compose.yml` and consists of three primary services:
- **`postgres`**: Relational database running PostgreSQL 18.4.
- **`backend`**: FastAPI application server executing database migrations and startup seeds before launching.
- **`frontend`**: React web application compiled and served via Vite preview.

---

## 2. Storage & Volumes Persistence

To prevent data loss across container teardown, persistent volumes are configured:
- **Database data**: Mapped to named volume `postgres_data`.
- **Uploaded files & documents**: Mapped to backend host folder `/app/uploads`.
- **System logs**: Mapped to backend host folder `/app/logs`.

---

## 3. Database Health-Check Policy

The backend service depends on PostgreSQL readiness. A dedicated script (`scripts/wait-for-db.sh`) pings the database connection using python-psycopg2 before executing Alembic migrations and database seeds.

---

## 4. Production Orchestration Example

For production deployments, it is recommended to run behind a reverse proxy (e.g. Nginx or Traefik) providing SSL certificates:

```text
[ Client (HTTPS) ]
        |
        v
[ Reverse Proxy (Nginx) ]
   |                |
   | (Port 80)      | (Port 80)
   v                v
[ Frontend ]   [ Backend ]
```
