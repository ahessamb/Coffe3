"""Human-readable logging for important backend business operations."""

import logging
from typing import Optional

logger = logging.getLogger("website.backend")


def _format_details(**kwargs) -> str:
    parts = []
    for key, value in kwargs.items():
        if value is None or value == "":
            continue
        if isinstance(value, str) and (" " in value or "," in value):
            parts.append(f'{key}="{value}"')
        else:
            parts.append(f"{key}={value}")
    return f" | {' | '.join(parts)}" if parts else ""


def _log(category: str, message: str, level: str = "info", **details) -> None:
    log_fn = getattr(logger, level, logger.info)
    log_fn("[%s] %s%s", category, message, _format_details(**details))


def log_exception(
    category: str,
    message: str,
    exc: Optional[BaseException] = None,
    **details,
) -> None:
    """Log an error with full exception type, message, and traceback to backend.log."""
    if exc is not None:
        details = dict(details)
        details["exception_type"] = type(exc).__name__
        if str(exc):
            details["exception"] = str(exc)
        exc_info: bool | tuple = (type(exc), exc, exc.__traceback__)
    else:
        exc_info = True

    logger.error(
        "[%s] %s%s",
        category,
        message,
        _format_details(**details),
        exc_info=exc_info,
    )


def log_cart(message: str, level: str = "info", **details) -> None:
    _log("CART", message, level, **details)


def log_checkout(message: str, level: str = "info", **details) -> None:
    _log("CHECKOUT", message, level, **details)


def log_order(message: str, level: str = "info", **details) -> None:
    _log("ORDER", message, level, **details)


def log_notification(message: str, level: str = "info", **details) -> None:
    _log("NOTIFICATION", message, level, **details)


def log_admin(message: str, level: str = "info", **details) -> None:
    _log("ADMIN", message, level, **details)


def log_startup(log_file: str) -> None:
    """Write a startup line so backend.log exists as soon as Django boots."""
    logger.info("[SYSTEM] Backend logging initialized | log_file=%s", log_file)
