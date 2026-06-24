import logging
import threading

import requests
from django.db import close_old_connections

from .models import SiteSettings, NotificationRecipient

logger = logging.getLogger(__name__)


def send_telegram_notification(order, action='new_order'):
    """Send order notification to Telegram recipients"""
    try:
        settings = SiteSettings.objects.first()

        if not settings or not settings.telegram_bot_token:
            return False

        # Get active Telegram recipients
        recipients = NotificationRecipient.objects.filter(
            platform='telegram',
            is_active=True
        )

        if not recipients.exists():
            return False

        # Prepare message based on action
        message = _prepare_message(order, action)

        # Send to all active Telegram recipients
        success_count = 0
        url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"

        for recipient in recipients:
            try:
                payload = {
                    'chat_id': recipient.chat_id,
                    'text': message,
                    'parse_mode': 'HTML'
                }

                response = requests.post(url, json=payload, timeout=10)

                if response.status_code == 200:
                    success_count += 1

            except Exception as e:
                print(f"Telegram notification error for {recipient.name}: {e}")
                continue

        # Mark as notified if at least one succeeded
        if success_count > 0 and not order.telegram_notified:
            order.telegram_notified = True
            order.save(update_fields=['telegram_notified'])

        return success_count > 0

    except Exception as e:
        print(f"Telegram notification error: {e}")
        return False


def send_bale_notification(order, action='new_order'):
    """Send order notification to Bale recipients"""
    try:
        settings = SiteSettings.objects.first()

        if not settings or not settings.bale_bot_token:
            return False

        # Get active Bale recipients
        recipients = NotificationRecipient.objects.filter(
            platform='bale',
            is_active=True
        )

        if not recipients.exists():
            return False

        # Prepare message based on action
        message = _prepare_message(order, action)

        # Send to all active Bale recipients
        success_count = 0
        url = f"https://tapi.bale.ai/bot{settings.bale_bot_token}/sendMessage"

        for recipient in recipients:
            try:
                payload = {
                    'chat_id': recipient.chat_id,
                    'text': message,
                    'parse_mode': 'HTML',
                }

                # Bale API is Telegram-like, but JSON body is not always accepted reliably.
                response = requests.post(url, data=payload, timeout=10)

                if response.status_code == 200:
                    success_count += 1
                else:
                    try:
                        data = response.json()
                        print(f"Bale API error for {recipient.name}: {data}")
                    except Exception:
                        print(f"Bale API HTTP error for {recipient.name}: {response.status_code} {response.text[:200]}")

            except Exception as e:
                print(f"Bale notification error for {recipient.name}: {e}")
                continue

        return success_count > 0

    except Exception as e:
        print(f"Bale notification error: {e}")
        return False


def send_all_notifications(order, action='new_order'):
    """Send notifications to both Telegram and Bale (synchronous)."""
    telegram_result = send_telegram_notification(order, action)
    bale_result = send_bale_notification(order, action)

    return telegram_result or bale_result


def _run_notifications_in_background(order_id, action):
    """Worker executed in a background thread."""
    close_old_connections()
    try:
        from .models import Order

        order = Order.objects.prefetch_related('items__product').get(pk=order_id)
        send_all_notifications(order, action=action)
    except Exception:
        logger.exception("Background notification failed for order %s (%s)", order_id, action)
    finally:
        close_old_connections()


def schedule_order_notifications(order, action='new_order'):
    """Queue Telegram/Bale notifications without blocking the current request."""
    order_id = order.pk if hasattr(order, 'pk') else order
    thread = threading.Thread(
        target=_run_notifications_in_background,
        args=(order_id, action),
        name=f"order-notify-{order_id}-{action}",
        daemon=True,
    )
    thread.start()


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