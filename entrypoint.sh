#!/bin/bash

echo "Waiting for postgres..."

while ! pg_isready -h db -p 5432 -U $DB_USER; do
  sleep 1
done

echo "PostgreSQL started"

# Apply database migrations
echo "Applying database migrations..."
python manage.py migrate

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --no-input

# Start server
echo "Starting server..."
python manage.py runserver 0.0.0.0:8000