"""Human-readable logging for important backend business operations.

Logging must never raise or block application flow — all paths are wrapped.
"""

import logging
from typing import Any, Optional

logger = logging.getLogger("website.backend")

# Keys that must not be passed through to logging internals or collide with helpers.
_RESERVED_DETAIL_KEYS = frozenset({
    "category",
    "message",
    "level",
    "exc",
    "exc_info",
    "log_tag",
    "name",
    "msg",
    "args",
    "created",
    "filename",
    "funcname",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "pathname",
    "process",
    "processname",
    "relativecreated",
    "thread",
    "threadname",
    "stack_info",
    "taskname",
    "asctime",
})


def format_log_value(value: Any) -> str:
    """Convert any value to a safe string for log output."""
    if value is None:
        return ""
    try:
        if hasattr(value, "all") and callable(getattr(value, "all")):
            try:
                items = list(value.all()[:20])
                if not items:
                    return "[]"
                return "[" + ", ".join(format_log_value(item) for item in items) + "]"
            except Exception:
                return repr(value)

        meta = getattr(value, "_meta", None)
        if meta is not None and hasattr(value, "pk"):
            for attr in ("title", "name", "slug", "username", "tracking_code"):
                label = getattr(value, attr, None)
                if label:
                    return f"{value.__class__.__name__}({label})"
            return f"{value.__class__.__name__}(pk={value.pk})"

        return str(value)
    except Exception:
        try:
            return repr(value)
        except Exception:
            return "<unprintable>"


def _safe_str(value: Any) -> str:
    return format_log_value(value)


def _sanitize_details(**details: Any) -> dict[str, Any]:
    sanitized: dict[str, Any] = {}
    for key, value in details.items():
        key_text = str(key)
        safe_key = (
            f"detail_{key_text}"
            if key_text.lower() in _RESERVED_DETAIL_KEYS
            else key_text
        )
        sanitized[safe_key] = _safe_str(value)
    return sanitized


def _flush_handlers() -> None:
    try:
        for handler in logger.handlers:
            handler.flush()
    except Exception:
        pass


def _format_details(**kwargs: Any) -> str:
    try:
        parts: list[str] = []
        for key, value in _sanitize_details(**kwargs).items():
            if value is None or value == "":
                continue
            text = _safe_str(value)
            if " " in text or "," in text or "|" in text or "=" in text:
                parts.append(f'{key}="{text}"')
            else:
                parts.append(f"{key}={text}")
        return f" | {' | '.join(parts)}" if parts else ""
    except Exception:
        return ""


def _emit(log_tag: str, message: str, level: str = "info", **details: Any) -> None:
    try:
        log_fn = getattr(logger, str(level), logger.info)
        if not callable(log_fn):
            log_fn = logger.info
        log_fn("[%s] %s%s", str(log_tag), str(message), _format_details(**details))
    except Exception:
        pass
    finally:
        _flush_handlers()


def _log(log_tag: str, message: str, level: str = "info", **details: Any) -> None:
    try:
        _emit(log_tag, message, level, **details)
    except Exception:
        pass


def log_exception(
    log_tag: str,
    message: str,
    exc: Optional[BaseException] = None,
    **details: Any,
) -> None:
    """Log an error with exception type, message, and traceback."""
    try:
        safe_details = _sanitize_details(**details)
        if exc is not None:
            safe_details["exception_type"] = type(exc).__name__
            exc_text = str(exc)
            if exc_text:
                safe_details["exception"] = exc_text
            exc_info: bool | tuple = (type(exc), exc, exc.__traceback__)
        else:
            exc_info = True

        logger.error(
            "[%s] %s%s",
            str(log_tag),
            str(message),
            _format_details(**safe_details),
            exc_info=exc_info,
        )
    except Exception:
        pass
    finally:
        _flush_handlers()


def log_cart(message: str, level: str = "info", **details: Any) -> None:
    try:
        _log("CART", message, level, **details)
    except Exception:
        pass


def log_checkout(message: str, level: str = "info", **details: Any) -> None:
    try:
        _log("CHECKOUT", message, level, **details)
    except Exception:
        pass


def log_order(message: str, level: str = "info", **details: Any) -> None:
    try:
        _log("ORDER", message, level, **details)
    except Exception:
        pass


def log_notification(message: str, level: str = "info", **details: Any) -> None:
    try:
        _log("NOTIFICATION", message, level, **details)
    except Exception:
        pass


def log_admin(message: str, level: str = "info", **details: Any) -> None:
    try:
        _log("ADMIN", message, level, **details)
    except Exception:
        pass


def log_startup(log_file: str) -> None:
    """Write a startup line so backend.log exists as soon as Django boots."""
    try:
        logger.info("[SYSTEM] Backend logging initialized | log_file=%s", str(log_file))
    except Exception:
        pass
    finally:
        _flush_handlers()
