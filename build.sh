#!/usr/bin/env bash
# build.sh - Скрипт сборки для Render.com

set -o errexit  # Остановка скрипта при первой ошибке

echo "Installing requirements..."
pip install -r requirements.txt

echo "Collecting static files..."
python manage.py collectstatic --no-input

echo "Running migrations..."
python manage.py migrate

echo "Seeding demo data (idempotent)..."
python manage.py seed_demo

echo "Build complete."
