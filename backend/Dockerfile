FROM python:3.11-slim as builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.11-slim as runner

WORKDIR /app

ENV PATH=/root/.local/bin:$PATH
ENV PYTHONPATH=/app

COPY --from=builder /root/.local /root/.local
COPY backend/ .
COPY scripts/ /app/scripts/

RUN chmod +x /app/scripts/wait-for-db.sh /app/scripts/run-migrations.sh

EXPOSE 8000

CMD ["sh", "-c", "/app/scripts/wait-for-db.sh && /app/scripts/run-migrations.sh && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
