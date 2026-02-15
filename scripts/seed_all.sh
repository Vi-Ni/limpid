#!/usr/bin/env bash
# Run all seed management commands
set -euo pipefail

echo "Seeding market data..."
python manage.py seed_securities

echo "Seeding education content..."
python manage.py seed_education

echo "Seeding impact directory..."
python manage.py seed_impact

echo "Done."
