import sys

from django.apps import AppConfig


class WebsiteConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "website"

    def ready(self):
        from django.conf import settings

        from .backend_log import log_startup

        log_dir = getattr(settings, "LOG_DIR", None)
        log_file = getattr(settings, "BACKEND_LOG_FILE", None)
        if not log_dir or not log_file:
            return

        try:
            log_dir.mkdir(exist_ok=True, mode=0o775)
            log_startup(str(log_file))
        except OSError as exc:
            print(
                f"WARNING: backend.log unavailable ({log_file}): {exc}",
                file=sys.stderr,
            )
