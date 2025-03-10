#!/usr/bin/env bash
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Create a local database if DATABASE_URL is not set
if [ -z "$DATABASE_URL" ]; then
    echo "No DATABASE_URL set, using SQLite"
fi

# Enhanced static files handling
echo "Setting up static files..."
# Create static directories if they don't exist
mkdir -p static
mkdir -p staticfiles

# No need to copy files from app directories since static is in the root

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --no-input --clear

# Create initial migrations for apps without migrations
echo "Creating initial migrations for apps..."
python manage.py makemigrations accounts
python manage.py makemigrations members
python manage.py makemigrations savings
python manage.py makemigrations loans
python manage.py makemigrations mono

# Run migrations with more verbose output and in a specific order
echo "Running migrations..."
python manage.py migrate auth --noinput
python manage.py migrate contenttypes --noinput
python manage.py migrate admin --noinput
python manage.py migrate sessions --noinput
python manage.py migrate --noinput

# Create superuser if needed (optional)
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ] && [ -n "$DJANGO_SUPERUSER_EMAIL" ]; then
    echo "Creating superuser..."
    python manage.py createsuperuser --noinput
fi

echo "Build completed successfully!"