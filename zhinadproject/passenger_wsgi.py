"""
cPanel / Phusion Passenger entry point.

In cPanel → Setup Python App:
  Application startup file: passenger_wsgi.py
  Application Entry point:  application
"""

import os
import sys

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
if APP_ROOT not in sys.path:
    sys.path.insert(0, APP_ROOT)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "zhinadproject.settings")

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
