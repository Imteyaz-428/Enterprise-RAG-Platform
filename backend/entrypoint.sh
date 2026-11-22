#!/bin/sh
set -e

echo "Applying Alembic database migrations..."
alembic upgrade head

echo "Starting server..."
if [ "$1" = "uvicorn" ]; then
    exec "$@"
elif [ $# -gt 0 ]; then
    exec uvicorn app:app --host 0.0.0.0 --port 8000 "$@"
else
    exec uvicorn app:app --host 0.0.0.0 --port 8000
fi
