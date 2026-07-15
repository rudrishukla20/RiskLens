#!/bin/sh
# wait-for-db.sh

set -e

host="${POSTGRES_HOST:-postgres}"
port="${POSTGRES_PORT:-5432}"

echo "Waiting for PostgreSQL at $host:$port..."

until python -c "
import sys
import psycopg2
try:
    conn = psycopg2.connect(
        host='$host',
        port=int('$port'),
        user='${POSTGRES_USER}',
        password='${POSTGRES_PASSWORD}',
        dbname='${POSTGRES_DB}',
        connect_timeout=3
    )
    conn.close()
    sys.exit(0)
except Exception as e:
    sys.exit(1)
" >/dev/null 2>&1; do
  echo "PostgreSQL is unavailable - sleeping"
  sleep 1
done

echo "PostgreSQL is up and accepting connections!"
