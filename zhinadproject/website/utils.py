import json
import os
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

import requests
from django.db import close_old_connections

from .models import SiteSettings, NotificationRecipient
from .backend_log import log_exception, log_notification

# When api.telegram.org is filtered, TCP connect can hang far longer than a single
# read timeout. Use short connect timeouts and a hard wall-clock cap for Telegram.
TELEGRAM_CONNECT_TIMEOUT = float(os.environ.get("TELEGRAM_CONNECT_TIMEOUT", "3"))
TELEGRAM_READ_TIMEOUT = float(os.environ.get("TELEGRAM_READ_TIMEOUT", "5"))
TELEGRAM_DEADLINE_SECONDS = float(os.environ.get("TELEGRAM_DEADLINE_SECONDS", "8"))
BALE_CONNECT_TIMEOUT = float(os.environ.get("BALE_CONNECT_TIMEOUT", "5"))
BALE_READ_TIMEOUT = float(os.environ.get("BALE_READ_TIMEOUT", "10"))
REQUEST_TIMEOUT = (TELEGRAM_CONNECT_TIMEOUT, TELEGRAM_READ_TIMEOUT)
BALE_REQUEST_TIMEOUT = (BALE_CONNECT_TIMEOUT, BALE_READ_TIMEOUT)


def _mask_token(token: str) -> str:
    if not token:
        return "NOT SET"
    token = token.strip()
    if len(token) <= 8:
        return f"SET({len(token)} chars)"
    return f"SET({len(token)} chars, ends ...{token[-4:]})"


def _notification_context(order, action, recipient=None, platform_name=None):
    ctx = {
        "order_id": getattr(order, "id", None),
        "tracking_code": getattr(order, "tracking_code", None),
        "action": action,
    }
    if platform_name:
        ctx["platform"] = platform_name
    if recipient is not None:
        ctx["recipient"] = recipient.name
        ctx["recipient_id"] = recipient.id
        ctx["chat_id"] = recipient.chat_id
    return ctx


def _telegram_disabled():
    return os.environ.get("SKIP_TELEGRAM_NOTIFICATIONS", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def _run_with_deadline(func, *, deadline_seconds, label, order, action):
    """Run a notification sender with a wall-clock cap so blocked APIs cannot stall Bale."""
    with ThreadPoolExecutor(max_workers=1, thread_name_prefix="notify-deadline") as pool:
        future = pool.submit(func, order, action)
        try:
            return future.result(timeout=deadline_seconds)
        except FuturesTimeoutError:
            reason = (
                f"{label}: skipped — blocked or unreachable "
                f"(no response within {deadline_seconds:g}s)"
            )
            log_notification(
                reason,
                level="warning",
                **_notification_context(order, action, platform_name=label.lower()),
                deadline_seconds=deadline_seconds,
            )
            return False, reason
        except Exception as exc:
            reason = f"{label}: unhandled error in deadline wrapper: {exc}"
            log_exception(
                "NOTIFICATION",
                reason,
                exc=exc,
                **_notification_context(order, action, platform_name=label.lower()),
            )
            return False, reason


def _parse_response_body(response):
    try:
        body = response.json()
        if isinstance(body, dict):
            return body
        return {"raw_json": body}
    except Exception:
        return {"raw_text": (response.text or "")[:1000]}


def _telegram_api_success(body, http_status):
    if isinstance(body, dict) and "ok" in body:
        return bool(body.get("ok"))
    return http_status == 200


def _bale_api_success(body, http_status):
    if isinstance(body, dict):
        if "ok" in body:
            return bool(body.get("ok"))
        if body.get("error"):
            return False
    return http_status == 200


def _failure_details(body, http_status):
    if not isinstance(body, dict):
        return {
            "http_status": http_status,
            "response_body": str(body)[:1000],
        }

    return {
        "http_status": http_status,
        "api_ok": body.get("ok"),
        "error_code": body.get("error_code") or body.get("code"),
        "description": body.get("description") or body.get("error") or body.get("message"),
        "response_body": json.dumps(body, ensure_ascii=False)[:1000],
    }


def _success_details(body, http_status):
    details = {"http_status": http_status}
    if isinstance(body, dict):
        result = body.get("result")
        if isinstance(result, dict):
            details["message_id"] = result.get("message_id")
        details["api_ok"] = body.get("ok", True)
    return details


def _log_platform_config(platform_name, token, recipients):
    recipient_list = [
        f"{r.name}(id={r.id}, chat_id={r.chat_id})"
        for r in recipients
    ]
    log_notification(
        f"{platform_name} config",
        platform=platform_name,
        token=_mask_token(token),
        active_recipients=len(recipient_list),
        recipients="; ".join(recipient_list) if recipient_list else "NONE",
    )


def _send_to_recipient(
    *,
    platform_label,
    platform_name,
    order,
    action,
    recipient,
    url,
    message,
    use_json,
    is_success,
    request_timeout,
):
    endpoint = url.split("/bot", 1)[0] + "/bot***/sendMessage"
    log_notification(
        f"{platform_label} HTTP request",
        platform=platform_name,
        endpoint=endpoint,
        chat_id=recipient.chat_id,
        message_length=len(message),
        payload_format="json" if use_json else "form",
    )

    payload = {
        "chat_id": recipient.chat_id,
        "text": message,
        "parse_mode": "HTML",
    }

    try:
        if use_json:
            response = requests.post(url, json=payload, timeout=request_timeout)
        else:
            response = requests.post(url, data=payload, timeout=request_timeout)
    except requests.Timeout as exc:
        connect_s, read_s = request_timeout
        reason = (
            f"{platform_label} timeout for chat_id={recipient.chat_id} "
            f"(connect={connect_s}s, read={read_s}s)"
        )
        log_exception(
            "NOTIFICATION",
            reason,
            exc=exc,
            **_notification_context(order, action, recipient, platform_name),
        )
        return False, reason
    except requests.RequestException as exc:
        reason = f"{platform_label} HTTP error for chat_id={recipient.chat_id}: {exc}"
        log_exception(
            "NOTIFICATION",
            reason,
            exc=exc,
            **_notification_context(order, action, recipient, platform_name),
        )
        return False, reason
    except Exception as exc:
        reason = f"{platform_label} unexpected error for chat_id={recipient.chat_id}: {exc}"
        log_exception(
            "NOTIFICATION",
            reason,
            exc=exc,
            **_notification_context(order, action, recipient, platform_name),
        )
        return False, reason

    body = _parse_response_body(response)
    if is_success(body, response.status_code):
        log_notification(
            f"{platform_label} delivered OK",
            **_notification_context(order, action, recipient, platform_name),
            **_success_details(body, response.status_code),
        )
        return True, "ok"

    details = _failure_details(body, response.status_code)
    reason = (
        f"{platform_label} API error chat_id={recipient.chat_id}: "
        f"HTTP {details.get('http_status')} | "
        f"code={details.get('error_code')} | "
        f"desc={details.get('description')}"
    )
    log_notification(
        f"{platform_label} ROOT CAUSE",
        level="error",
        reason=reason,
        **_notification_context(order, action, recipient, platform_name),
        **details,
    )
    return False, reason


def send_telegram_notification(order, action="new_order"):
    """Send order notification to Telegram recipients. Returns (success, reason)."""
    platform_label = "Telegram"
    platform_name = "telegram"

    if _telegram_disabled():
        reason = "Telegram: skipped — SKIP_TELEGRAM_NOTIFICATIONS is enabled on server"
        log_notification(
            reason,
            level="warning",
            **_notification_context(order, action, platform_name=platform_name),
        )
        return False, reason

    log_notification(
        f"{platform_label} step 1: start",
        **_notification_context(order, action, platform_name=platform_name),
    )

    try:
        settings = SiteSettings.objects.first()
        log_notification(
            f"{platform_label} step 2: loaded SiteSettings",
            settings_found=bool(settings),
            **_notification_context(order, action, platform_name=platform_name),
        )

        if not settings:
            reason = "Telegram: SiteSettings row missing in database"
            log_notification(reason, level="error", **_notification_context(order, action, platform_name=platform_name))
            return False, reason

        token = (settings.telegram_bot_token or "").strip()
        recipients = list(
            NotificationRecipient.objects.filter(platform="telegram", is_active=True)
        )
        _log_platform_config(platform_name, token, recipients)

        if not token:
            reason = "Telegram: bot token is empty (Admin -> Site Settings -> Telegram bot token)"
            log_notification(reason, level="error", **_notification_context(order, action, platform_name=platform_name))
            return False, reason

        if not recipients:
            reason = "Telegram: no active recipients (Admin -> Notification Recipients -> add telegram chat_id)"
            log_notification(reason, level="error", **_notification_context(order, action, platform_name=platform_name))
            return False, reason

        try:
            message = _prepare_message(order, action)
        except Exception as exc:
            reason = f"Telegram: message preparation failed: {exc}"
            log_exception("NOTIFICATION", reason, exc=exc, **_notification_context(order, action, platform_name=platform_name))
            return False, reason

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        success_count = 0
        failure_reasons = []

        log_notification(
            f"{platform_label} step 3: dispatching",
            recipients=len(recipients),
            message_length=len(message),
            **_notification_context(order, action, platform_name=platform_name),
        )

        for recipient in recipients:
            ok, recipient_reason = _send_to_recipient(
                platform_label=platform_label,
                platform_name=platform_name,
                order=order,
                action=action,
                recipient=recipient,
                url=url,
                message=message,
                use_json=True,
                is_success=_telegram_api_success,
                request_timeout=REQUEST_TIMEOUT,
            )
            if ok:
                success_count += 1
            else:
                failure_reasons.append(recipient_reason)
                # When Telegram is filtered, fail fast — do not block Bale.
                if "timeout" in recipient_reason.lower() or "HTTP error" in recipient_reason:
                    log_notification(
                        "Telegram: stopping early after unreachable/blocked response",
                        level="warning",
                        reason=recipient_reason,
                        **_notification_context(order, action, platform_name=platform_name),
                    )
                    break

        if success_count > 0 and not order.telegram_notified:
            order.telegram_notified = True
            order.save(update_fields=["telegram_notified"])

        if success_count > 0:
            reason = f"Telegram: sent to {success_count}/{len(recipients)} recipient(s)"
            log_notification(reason, **_notification_context(order, action, platform_name=platform_name))
            return True, reason

        reason = "Telegram: all failed — " + (" | ".join(failure_reasons) if failure_reasons else "unknown")
        log_notification(reason, level="error", **_notification_context(order, action, platform_name=platform_name))
        return False, reason

    except Exception as exc:
        reason = f"Telegram: unhandled error: {exc}"
        log_exception("NOTIFICATION", reason, exc=exc, **_notification_context(order, action, platform_name=platform_name))
        return False, reason


def send_bale_notification(order, action="new_order"):
    """Send order notification to Bale recipients. Returns (success, reason)."""
    platform_label = "Bale"
    platform_name = "bale"
    log_notification(
        f"{platform_label} step 1: start",
        **_notification_context(order, action, platform_name=platform_name),
    )

    try:
        settings = SiteSettings.objects.first()
        log_notification(
            f"{platform_label} step 2: loaded SiteSettings",
            settings_found=bool(settings),
            **_notification_context(order, action, platform_name=platform_name),
        )

        if not settings:
            reason = "Bale: SiteSettings row missing in database"
            log_notification(reason, level="error", **_notification_context(order, action, platform_name=platform_name))
            return False, reason

        token = (settings.bale_bot_token or "").strip()
        recipients = list(
            NotificationRecipient.objects.filter(platform="bale", is_active=True)
        )
        _log_platform_config(platform_name, token, recipients)

        if not token:
            reason = "Bale: bot token is empty (Admin -> Site Settings -> Bale bot token)"
            log_notification(reason, level="error", **_notification_context(order, action, platform_name=platform_name))
            return False, reason

        if not recipients:
            reason = "Bale: no active recipients (Admin -> Notification Recipients -> add bale chat_id)"
            log_notification(reason, level="error", **_notification_context(order, action, platform_name=platform_name))
            return False, reason

        try:
            message = _prepare_message(order, action)
        except Exception as exc:
            reason = f"Bale: message preparation failed: {exc}"
            log_exception("NOTIFICATION", reason, exc=exc, **_notification_context(order, action, platform_name=platform_name))
            return False, reason

        url = f"https://tapi.bale.ai/bot{token}/sendMessage"
        success_count = 0
        failure_reasons = []

        log_notification(
            f"{platform_label} step 3: dispatching",
            recipients=len(recipients),
            message_length=len(message),
            **_notification_context(order, action, platform_name=platform_name),
        )

        for recipient in recipients:
            ok, recipient_reason = _send_to_recipient(
                platform_label=platform_label,
                platform_name=platform_name,
                order=order,
                action=action,
                recipient=recipient,
                url=url,
                message=message,
                use_json=False,
                is_success=_bale_api_success,
                request_timeout=BALE_REQUEST_TIMEOUT,
            )
            if ok:
                success_count += 1
            else:
                failure_reasons.append(recipient_reason)

        if success_count > 0:
            reason = f"Bale: sent to {success_count}/{len(recipients)} recipient(s)"
            log_notification(reason, **_notification_context(order, action, platform_name=platform_name))
            return True, reason

        reason = "Bale: all failed — " + (" | ".join(failure_reasons) if failure_reasons else "unknown")
        log_notification(reason, level="error", **_notification_context(order, action, platform_name=platform_name))
        return False, reason

    except Exception as exc:
        reason = f"Bale: unhandled error: {exc}"
        log_exception("NOTIFICATION", reason, exc=exc, **_notification_context(order, action, platform_name=platform_name))
        return False, reason


def send_all_notifications(order, action="new_order"):
    """Send notifications to both Telegram and Bale (synchronous)."""
    log_notification(
        "Notification batch started",
        order_id=order.id,
        tracking_code=order.tracking_code,
        action=action,
    )

    telegram_ok, telegram_reason = _run_with_deadline(
        send_telegram_notification,
        deadline_seconds=TELEGRAM_DEADLINE_SECONDS,
        label="Telegram",
        order=order,
        action=action,
    )

    log_notification(
        "Telegram phase done — starting Bale",
        order_id=order.id,
        tracking_code=order.tracking_code,
        telegram_ok=telegram_ok,
        telegram_reason=telegram_reason,
    )

    bale_ok, bale_reason = send_bale_notification(order, action)

    overall_ok = telegram_ok or bale_ok
    log_notification(
        "Notification batch completed",
        level="error" if not overall_ok else "info",
        order_id=order.id,
        tracking_code=order.tracking_code,
        action=action,
        telegram_ok=telegram_ok,
        telegram_reason=telegram_reason,
        bale_ok=bale_ok,
        bale_reason=bale_reason,
    )

    return overall_ok


def schedule_order_notifications(order, action="new_order"):
    """Send Telegram/Bale notifications in the same request (reliable on cPanel/Passenger)."""
    order_id = order.pk if hasattr(order, "pk") else order
    log_notification(
        "Sending notifications now (sync)",
        order_id=order_id,
        tracking_code=getattr(order, "tracking_code", None),
        action=action,
    )

    close_old_connections()
    try:
        send_all_notifications(order, action=action)
    except Exception as exc:
        log_exception(
            "NOTIFICATION",
            f"Notification dispatch crashed: {exc}",
            exc=exc,
            order_id=order_id,
            tracking_code=getattr(order, "tracking_code", None),
            action=action,
        )
    finally:
        close_old_connections()


def _prepare_message(order, action):
    """Prepare notification message based on action"""
    if action == 'pending_order':
        message = f"""
🛍 سفارش جدید — در انتظار پرداخت

📋 کد پیگیری: {order.tracking_code}
👤 مشتری: {order.customer_name}
📞 تلفن: {order.phone_number}
📞 تلفن دوم: {order.phone_number_2 or '—'}
📍 آدرس: {order.address}
📝 یادداشت مشتری: {order.additional_notes or '—'}
💰 مبلغ محصولات: {order.total_price:,} تومان

📦 محصولات:
"""
        for item in order.items.all():
            subtitle = f" ({item.product.subtitle})" if item.product.subtitle else ""
            message += f"• {item.product.title}{subtitle} — {item.quantity} عدد — {item.get_subtotal():,} تومان\n"

        message += f"\n⏰ زمان ثبت: {order.created_at.strftime('%Y/%m/%d - %H:%M')}"

    elif action == 'new_order':
        transaction_line = order.transaction_id or '—'
        purchased_at = order.purchased_at or order.created_at
        message = f"""
🛍 سفارش جدید — پرداخت شده

📋 کد پیگیری: {order.tracking_code}
👤 مشتری: {order.customer_name}
📞 تلفن: {order.phone_number}
💰 مبلغ: {order.total_price:,} تومان
🔢 شماره پیگیری تراکنش: {transaction_line}

📦 محصولات:
"""
        for item in order.items.all():
            subtitle = f" ({item.product.subtitle})" if item.product.subtitle else ""
            message += f"• {item.product.title}{subtitle} — {item.quantity} عدد\n"

        message += f"\n⏰ زمان: {purchased_at.strftime('%Y/%m/%d - %H:%M')}"

    elif action == 'confirmed':
        message = f"""
✅ سفارش تایید شد

📋 کد پیگیری: {order.tracking_code}
👤 مشتری: {order.customer_name}
📍 آدرس: {order.address}
📝 یادداشت مشتری: {order.additional_notes}
💰 مبلغ: {order.total_price:,} تومان

وضعیت: تایید شده و در حال آماده‌سازی
"""

    elif action == 'processing':
        message = f"""
⚙️ سفارش در حال آماده‌سازی

📋 کد پیگیری: {order.tracking_code}
👤 مشتری: {order.customer_name}
💰 مبلغ: {order.total_price:,} تومان

وضعیت: در حال آماده‌سازی
"""

    elif action == 'shipped':
        message = f"""
🚚 سفارش ارسال شد

📋 کد پیگیری: {order.tracking_code}
👤 مشتری: {order.customer_name}
💰 مبلغ: {order.total_price:,} تومان

وضعیت: ارسال شده
"""

    elif action == 'delivered':
        message = f"""
✅ سفارش تحویل داده شد

📋 کد پیگیری: {order.tracking_code}
👤 مشتری: {order.customer_name}
💰 مبلغ: {order.total_price:,} تومان

وضعیت: تحویل داده شده
"""

    elif action == 'cancelled':
        message = f"""
❌ سفارش لغو شد

📋 کد پیگیری: {order.tracking_code}
👤 مشتری: {order.customer_name}
💰 مبلغ: {order.total_price:,} تومان

وضعیت: لغو شده
"""

    else:
        message = f"سفارش {order.tracking_code} - وضعیت: {order.get_status_display()}"

    return message
