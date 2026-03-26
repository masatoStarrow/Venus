#!/bin/bash
set -e

echo "Running Venus (Interactions Service) migrations..."
alembic upgrade head

echo "Starting Venus with Uvicorn..."
exec uvicorn main:app --host 0.0.0.0 --port 8002 --workers 1
