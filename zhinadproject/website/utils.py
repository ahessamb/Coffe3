import json
import threading

import requests
from django.db import close_old_connections

from .models import SiteSettings, NotificationRecipient
from .backend_log import log_exception, log_notification


def _mask_token(token: str) -> str:
    if not token:
        return "NOT SET"
    token = token.strip()
    if len(token) <= 8:
        return f"SET({len(token)} chars)"
    return f"SET({len(token)} chars, ends ...{token[-4:]})"


def _notification_context(order, action, recipient=None, platform=None):
    ctx = {
        "order_id": getattr(order, "id", None),
        "tracking_code": getattr(order, "tracking_code", None),
        "action": action,
    }
    if platform:
        ctx["platform"] = platform
    if recipient is not None:
        ctx["recipient"] = recipient.name
        ctx["recipient_id"] = recipient.id
        ctx["chat_id"] = recipient.chat_id
    return ctx


def _parse_response_body(response):
    """Return parsed JSON body or a fallback dict with raw text."""
    try:
        body = response.json()
        if isinstance(body, dict):
            return body
        return {"raw_json": body}
    except Exception:
        return {"raw_text": (response.text or "")[:1000]}


def _telegram_api_success(body, http_status):
    """Telegram often returns HTTP 200 even when the API call failed."""
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


def _log_platform_config(platform, token, recipients):
    recipient_list = [
        f"{r.name}(id={r.id}, chat_id={r.chat_id})"
        for r in recipients
    ]
    inactive_count = NotificationRecipient.objects.filter(
        platform=platform,
        is_active=False,
    ).count()

    log_notification(
        f"{platform} configuration check",
        platform=platform,
        token=_mask_token(token),
        active_recipients=len(recipient_list),
        inactive_recipients=inactive_count,
        recipients="; ".join(recipient_list) if recipient_list else "NONE",
    )


def _log_outgoing_request(platform, endpoint, chat_id, message, use_json):
    log_notification(
        f"{platform} sending HTTP request",
        platform=platform,
        endpoint=endpoint,
        chat_id=chat_id,
        message_length=len(message),
        payload_format="json" if use_json else "form",
        parse_mode="HTML",
    )


def _send_to_recipient(
    *,
    platform,
    order,
    action,
    recipient,
    url,
    message,
    use_json,
    is_success,
):
    _log_outgoing_request(
        platform,
        endpoint=url.split("/bot", 1)[0] + "/bot***/sendMessage",
        chat_id=recipient.chat_id,
        message=message,
        use_json=use_json,
    )

    payload = {
        "chat_id": recipient.chat_id,
        "text": message,
        "parse_mode": "HTML",
    }

    try:
        if use_json:
            response = requests.post(url, json=payload, timeout=15)
        else:
            response = requests.post(url, data=payload, timeout=15)
    except requests.Timeout as exc:
        log_exception(
            "NOTIFICATION",
            f"{platform} request timed out after 15s",
            exc=exc,
            **_notification_context(order, action, recipient, platform),
            endpoint=url.split("/bot", 1)[0] + "/bot***/sendMessage",
        )
        return False
    except requests.RequestException as exc:
        log_exception(
            "NOTIFICATION",
            f"{platform} HTTP request failed",
            exc=exc,
            **_notification_context(order, action, recipient, platform),
            endpoint=url.split("/bot", 1)[0] + "/bot***/sendMessage",
        )
        return False
    except Exception as exc:
        log_exception(
            "NOTIFICATION",
            f"{platform} unexpected error during HTTP request",
            exc=exc,
            **_notification_context(order, action, recipient, platform),
        )
        return False

    body = _parse_response_body(response)
    success = is_success(body, response.status_code)

    if success:
        log_notification(
            f"{platform} message delivered successfully",
            **_notification_context(order, action, recipient, platform),
            **_success_details(body, response.status_code),
        )
        return True

    log_notification(
        f"{platform} API rejected the message — ROOT CAUSE",
        level="error",
        **_notification_context(order, action, recipient, platform),
        **_failure_details(body, response.status_code),
    )
    return False


def send_telegram_notification(order, action="new_order"):
    """Send order notification to Telegram recipients."""
    platform = "Telegram"
    try:
        settings = SiteSettings.objects.first()

        if not settings:
            log_notification(
                "Telegram skipped — SiteSettings row missing in database",
                level="error",
                **_notification_context(order, action, platform="telegram"),
            )
            return False

        token = (settings.telegram_bot_token or "").strip()
        recipients = list(
            NotificationRecipient.objects.filter(platform="telegram", is_active=True)
        )

        _log_platform_config("telegram", token, recipients)

        if not token:
            log_notification(
                "Telegram skipped — bot token is empty in SiteSettings",
                level="error",
                **_notification_context(order, action, platform="telegram"),
                fix="Admin → Site Settings → Telegram bot token",
            )
            return False

        if not recipients:
            log_notification(
                "Telegram skipped — no active recipients configured",
                level="error",
                **_notification_context(order, action, platform="telegram"),
                fix="Admin → Notification Recipients → add telegram recipient with chat_id",
            )
            return False

        try:
            message = _prepare_message(order, action)
        except Exception as exc:
            log_exception(
                "NOTIFICATION",
                "Telegram message preparation failed",
                exc=exc,
                **_notification_context(order, action, platform="telegram"),
            )
            return False

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        success_count = 0
        failure_count = 0

        log_notification(
            "Telegram dispatch started",
            **_notification_context(order, action, platform="telegram"),
            recipients=len(recipients),
            message_length=len(message),
        )

        for recipient in recipients:
            if _send_to_recipient(
                platform=platform,
                order=order,
                action=action,
                recipient=recipient,
                url=url,
                message=message,
                use_json=True,
                is_success=_telegram_api_success,
            ):
                success_count += 1
            else:
                failure_count += 1

        if success_count > 0 and not order.telegram_notified:
            order.telegram_notified = True
            order.save(update_fields=["telegram_notified"])

        log_notification(
            "Telegram dispatch finished",
            level="error" if success_count == 0 else "info",
            **_notification_context(order, action, platform="telegram"),
            sent=success_count,
            failed=failure_count,
            total=len(recipients),
        )
        return success_count > 0

    except Exception as exc:
        log_exception(
            "NOTIFICATION",
            "Telegram notification failed — unhandled error",
            exc=exc,
            **_notification_context(order, action, platform="telegram"),
        )
        return False


def send_bale_notification(order, action="new_order"):
    """Send order notification to Bale recipients."""
    platform = "Bale"
    try:
        settings = SiteSettings.objects.first()

        if not settings:
            log_notification(
                "Bale skipped — SiteSettings row missing in database",
                level="error",
                **_notification_context(order, action, platform="bale"),
            )
            return False

        token = (settings.bale_bot_token or "").strip()
        recipients = list(
            NotificationRecipient.objects.filter(platform="bale", is_active=True)
        )

        _log_platform_config("bale", token, recipients)

        if not token:
            log_notification(
                "Bale skipped — bot token is empty in SiteSettings",
                level="error",
                **_notification_context(order, action, platform="bale"),
                fix="Admin → Site Settings → Bale bot token",
            )
            return False

        if not recipients:
            log_notification(
                "Bale skipped — no active recipients configured",
                level="error",
                **_notification_context(order, action, platform="bale"),
                fix="Admin → Notification Recipients → add bale recipient with chat_id",
            )
            return False

        try:
            message = _prepare_message(order, action)
        except Exception as exc:
            log_exception(
                "NOTIFICATION",
                "Bale message preparation failed",
                exc=exc,
                **_notification_context(order, action, platform="bale"),
            )
            return False

        url = f"https://tapi.bale.ai/bot{token}/sendMessage"
        success_count = 0
        failure_count = 0

        log_notification(
            "Bale dispatch started",
            **_notification_context(order, action, platform="bale"),
            recipients=len(recipients),
            message_length=len(message),
        )

        for recipient in recipients:
            if _send_to_recipient(
                platform=platform,
                order=order,
                action=action,
                recipient=recipient,
                url=url,
                message=message,
                use_json=False,
                is_success=_bale_api_success,
            ):
                success_count += 1
            else:
                failure_count += 1

        log_notification(
            "Bale dispatch finished",
            level="error" if success_count == 0 else "info",
            **_notification_context(order, action, platform="bale"),
            sent=success_count,
            failed=failure_count,
            total=len(recipients),
        )
        return success_count > 0

    except Exception as exc:
        log_exception(
            "NOTIFICATION",
            "Bale notification failed — unhandled error",
            exc=exc,
            **_notification_context(order, action, platform="bale"),
        )
        return False


def send_all_notifications(order, action="new_order"):
    """Send notifications to both Telegram and Bale (synchronous)."""
    log_notification(
        "Notification batch started",
        order_id=order.id,
        tracking_code=order.tracking_code,
        action=action,
    )

    telegram_result = send_telegram_notification(order, action)
    bale_result = send_bale_notification(order, action)

    log_notification(
        "Notification batch completed",
        level="error" if not (telegram_result or bale_result) else "info",
        order_id=order.id,
        tracking_code=order.tracking_code,
        action=action,
        telegram_success=telegram_result,
        bale_success=bale_result,
    )

    return telegram_result or bale_result


def _run_notifications_in_background(order_id, action):
    """Worker executed in a background thread."""
    from .models import Order

    close_old_connections()
    log_notification(
        "Background notification worker started",
        order_id=order_id,
        action=action,
        thread=threading.current_thread().name,
    )
    try:
        order = Order.objects.prefetch_related("items__product").get(pk=order_id)
        log_notification(
            "Background worker loaded order",
            order_id=order.id,
            tracking_code=order.tracking_code,
            action=action,
            item_count=order.items.count(),
        )
        send_all_notifications(order, action=action)
        log_notification(
            "Background notification worker finished successfully",
            order_id=order_id,
            action=action,
        )
    except Order.DoesNotExist as exc:
        log_exception(
            "NOTIFICATION",
            "Background worker failed — order not found in database",
            exc=exc,
            order_id=order_id,
            action=action,
        )
    except Exception as exc:
        log_exception(
            "NOTIFICATION",
            "Background notification worker failed",
            exc=exc,
            order_id=order_id,
            action=action,
        )
    finally:
        close_old_connections()


def schedule_order_notifications(order, action="new_order"):
    """Queue Telegram/Bale notifications without blocking the current request."""
    order_id = order.pk if hasattr(order, "pk") else order
    log_notification(
        "Scheduling background notifications",
        order_id=order_id,
        tracking_code=getattr(order, "tracking_code", None),
        action=action,
    )
    thread = threading.Thread(
        target=_run_notifications_in_background,
        args=(order_id, action),
        name=f"order-notify-{order_id}-{action}",
        daemon=True,
    )
    thread.start()
    log_notification(
        "Background notification thread launched",
        order_id=order_id,
        action=action,
        thread=thread.name,
        daemon=True,
    )


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
