#!/bin/bash
# Run from cPanel Terminal AFTER activating the Python app virtualenv.
# Usage:
#   cd ~/Coffe3/zhinadproject
#   source /home/USER/virtualenv/.../bin/activate
#   bash scripts/cpanel_post_install.sh

set -euo pipefail

cd "$(dirname "$0")/.."
echo "Working directory: $(pwd)"

pip install --upgrade pip
pip install -r ../requirements.txt

python manage.py migrate --noinput
python manage.py collectstatic --noinput

mkdir -p tmp logs
touch tmp/restart.txt

echo ""
echo "Done. Next steps:"
echo "  1. python manage.py createsuperuser   (if you have not yet)"
echo "  2. Restart the app in cPanel → Setup Python App"
echo "  3. Set Wagtail Site hostname in /cms/ → Settings → Sites"
