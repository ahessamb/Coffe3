import os
import sys

# cPanel/Passenger expects this file in the app root.
# Ensure the Django project package directory is importable.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, "zhinadproject"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "zhinadproject.settings")

from django.core.wsgi import get_wsgi_application  # noqa: E402

application = get_wsgi_application()

