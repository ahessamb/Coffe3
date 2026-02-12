import requests
from .models import SiteSettings


def send_telegram_notification(order, action='new_order'):
    """Send order notification to Telegram"""
    try:
        settings = SiteSettings.objects.first()

        if not settings or not settings.telegram_bot_token or not settings.telegram_chat_id:
            return False

        # Prepare message based on action
        if action == 'new_order':
            message = f"""
🛍 سفارش جدید ثبت شد!

📋 کد پیگیری: {order.tracking_code}
👤 مشتری: {order.customer_name}
📞 تلفن: {order.phone_number}
💰 مبلغ: {order.total_price:,} تومان
🔢 شماره پیگیری تراکنش: {order.transaction_id}

📦 محصولات:
"""
            for item in order.items.all():
                message += f"• {item.product.title} - ({item.product.subtitle}) {item.quantity} عدد\n"

            message += f"\n⏰ زمان: {order.purchased_at.strftime('%Y/%m/%d - %H:%M')}"

        elif action == 'confirmed':
            message = f"""
✅ سفارش تایید شد

📋 کد پیگیری: {order.tracking_code}
👤 مشتری: {order.customer_name}
👤 آدرس: {order.address}
👤 یادداشت مشتری: {order.additional_notes}
💰 مبلغ: {order.total_price:,} تومان

وضعیت: تایید شده و در حال آماده‌سازی
"""

        # Send to Telegram
        url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
        payload = {
            'chat_id': settings.telegram_chat_id,
            'text': message,
            'parse_mode': 'HTML'
        }

        response = requests.post(url, json=payload, timeout=10)

        if response.status_code == 200:
            if not order.telegram_notified:
                order.telegram_notified = True
                order.save(update_fields=['telegram_notified'])
            return True

        return False

    except Exception as e:
        print(f"Telegram notification error: {e}")
        return False