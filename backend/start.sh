#!/bin/bash
# Railway startup script
set -e

echo "Collecting static files..."
python manage.py collectstatic --noinput --settings=config.settings.production

echo "Starting Daphne ASGI server..."
exec daphne -b 0.0.0.0 -p "${PORT:-8000}" config.asgi:application
