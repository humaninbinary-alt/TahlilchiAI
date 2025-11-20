#!/bin/bash
# Docker entrypoint script for FastAPI application

set -e

echo "Starting TahlilchiAI RAG API..."

# Wait for database to be ready
echo "Waiting for PostgreSQL..."
while ! nc -z ${POSTGRES_SERVER:-postgres} ${POSTGRES_PORT:-5432}; do
    sleep 1
done
echo "PostgreSQL is ready!"

# Wait for Redis
echo "Waiting for Redis..."
while ! nc -z redis 6379; do
    sleep 1
done
echo "Redis is ready!"

# Run database migrations
echo "Running database migrations..."
alembic upgrade head

# Start application
echo "Starting uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
