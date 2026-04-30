#!/usr/bin/env sh
set -eu

python /app/zhinadproject/manage.py migrate --noinput
python /app/zhinadproject/manage.py collectstatic --noinput || true

exec python /app/zhinadproject/manage.py runserver 0.0.0.0:8000

