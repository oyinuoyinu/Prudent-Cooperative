#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt


# Create a local database if DATABASE_URL is not set
if [ -z "$DATABASE_URL" ]; then
    echo "No DATABASE_URL set, using SQLite"
fi

python manage.py collectstatic --no-input
python manage.py migrate