#!/bin/sh
# run-migrations.sh

set -e

echo "Running database migrations..."
alembic upgrade head

echo "Running database seeds..."
python -m app.seed.run_seed

echo "Migrations and seeds completed successfully!"
