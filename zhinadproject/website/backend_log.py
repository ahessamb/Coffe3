"""Human-readable logging for important backend business operations."""

import logging
from typing import Optional

logger = logging.getLogger("website.backend")


def _flush_handlers() -> None:
    for handler in logger.handlers:
        handler.flush()


def _format_details(**kwargs) -> str:
    parts = []
    for key, value in kwargs.items():
        if value is None or value == "":
            continue
        text = str(value)
        if " " in text or "," in text or "|" in text:
            parts.append(f'{key}="{text}"')
        else:
            parts.append(f"{key}={text}")
    return f" | {' | '.join(parts)}" if parts else ""


def _emit(level: str, category: str, message: str, **details) -> None:
    log_fn = getattr(logger, level, logger.info)
    try:
        log_fn("[%s] %s%s", category, message, _format_details(**details))
    except Exception as fallback_exc:
        logger.error(
            "[LOG_ERROR] Failed to write log line | category=%s | message=%s | error=%s",
            category,
            message,
            fallback_exc,
        )
    finally:
        _flush_handlers()


def _log(category: str, message: str, level: str = "info", **details) -> None:
    _emit(level, category, message, **details)


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

    try:
        logger.error(
            "[%s] %s%s",
            category,
            message,
            _format_details(**details),
            exc_info=exc_info,
        )
    except Exception as fallback_exc:
        logger.error("[LOG_ERROR] Failed to write exception log | error=%s", fallback_exc)
    finally:
        _flush_handlers()


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
    _flush_handlers()
