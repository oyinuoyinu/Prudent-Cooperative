

#!/usr/bin/env bash
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Create a local database if DATABASE_URL is not set
if [ -z "$DATABASE_URL" ]; then
    echo "No DATABASE_URL set, using SQLite"
fi

# Collect static files
python manage.py collectstatic --no-input

# Run migrations with more verbose output and in a specific order
echo "Running migrations..."
python manage.py makemigrations --noinput
python manage.py migrate auth --noinput
python manage.py migrate contenttypes --noinput
python manage.py migrate admin --noinput
python manage.py migrate sessions --noinput
python manage.py migrate accounts --noinput
python manage.py migrate members --noinput
python manage.py migrate savings --noinput
python manage.py migrate loans --noinput
python manage.py migrate mono --noinput
python manage.py migrate --noinput

# Create superuser if needed (optional)
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ] && [ -n "$DJANGO_SUPERUSER_EMAIL" ]; then
    echo "Creating superuser..."
    python manage.py createsuperuser --noinput
fi

echo "Build completed successfully!"

