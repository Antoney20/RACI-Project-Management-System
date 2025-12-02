#!/usr/bin/env bash
set -e

echo "Creating Django project with Poetry..."
poetry config virtualenvs.in-project true --local
poetry install --sync

echo "Creating Django project structure..."
poetry run django-admin startproject config .

echo "Creating first app 'core'..."
poetry run python manage.py startapp core

echo "Done! Now run:"
echo "   source .venv/bin/activate   # or just use 'poetry shell'"
echo "   make run"