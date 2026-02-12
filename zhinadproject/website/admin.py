from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from django.utils.safestring import mark_safe
from .models import Product, ProductImage, Order, OrderItem, SiteSettings, BlogPost
from .utils import send_telegram_notification


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ['image', 'alt_text', 'order']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'price', 'stock', 'is_active', 'created_at']
    list_filter = ['category', 'is_active', 'created_at']
    search_fields = ['title', 'description']
    prepopulated_fields = {'slug': ('title',)}
    inlines = [ProductImageInline]

    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('title', 'slug', 'subtitle', 'category')
        }),
        ('توضیحات و تصویر', {
            'fields': ('description', 'main_image')
        }),
        ('قیمت و موجودی', {
            'fields': ('price', 'stock', 'is_active')
        }),
    )


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['product', 'quantity', 'price', 'get_subtotal']
    can_delete = False

    def get_subtotal(self, obj):
        if obj.id:
            return format_html('<strong>{:,} تومان</strong>', obj.get_subtotal())
        return '-'

    get_subtotal.short_description = 'جمع'


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'tracking_code',
        'customer_name',
        'phone_number',
        'colored_status',
        'total_price_display',
        'created_at',
        'view_details_link'
    ]
    list_filter = ['status', 'created_at', 'confirmed_at']
    search_fields = ['customer_name', 'phone_number', 'tracking_code', 'transaction_id']
    readonly_fields = [
        'tracking_code',
        'created_at',
        'updated_at',
        'purchased_at',
        'confirmed_at',
        'total_price',
        'get_items_display'
    ]
    inlines = [OrderItemInline]
    actions = ['confirm_orders', 'mark_as_processing', 'mark_as_shipped', 'mark_as_delivered']

    fieldsets = (
        ('اطلاعات سفارش', {
            'fields': ('tracking_code', 'status', 'total_price', 'get_items_display')
        }),
        ('اطلاعات مشتری', {
            'fields': ('customer_name', 'phone_number', 'phone_number_2', 'address', 'additional_notes')
        }),
        ('اطلاعات پرداخت', {
            'fields': ('card_number', 'transaction_id', 'purchased_at', 'confirmed_at')
        }),
        ('یادداشت ادمین', {
            'fields': ('admin_notes',),
            'classes': ('collapse',)
        }),
        ('اطلاعات زمانی', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        # Show all orders except drafts in admin
        qs = super().get_queryset(request)
        return qs.exclude(status='draft')

    def colored_status(self, obj):
        colors = {
            'pending': '#FFA500',
            'purchased': '#2196F3',
            'confirmed': '#4CAF50',
            'processing': '#9C27B0',
            'shipped': '#00BCD4',
            'delivered': '#4CAF50',
            'cancelled': '#F44336',
        }
        color = colors.get(obj.status, '#666')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 5px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )

    colored_status.short_description = 'وضعیت'

    def total_price_display(self, obj):
        return format_html('<strong>{} تومان</strong>', str(obj.total_price))

    total_price_display.short_description = 'مبلغ کل'

    def view_details_link(self, obj):
        url = reverse('admin:website_order_change', args=[obj.id])
        return format_html('<a href="{}" style="color: #2196F3;">مشاهده جزئیات</a>', url)

    view_details_link.short_description = 'عملیات'

    def get_items_display(self, obj):
        if not obj.id:
            return '-'

        items_html = '<div style="margin-top: 10px;">'
        items_html += '<table style="width: 100%; border-collapse: collapse; background: white;">'
        items_html += '<thead><tr style="background-color: #f5f5f5;">'
        items_html += '<th style="padding: 10px; text-align: right; border: 1px solid #ddd;">محصول</th>'
        items_html += '<th style="padding: 10px; text-align: center; border: 1px solid #ddd;">تعداد</th>'
        items_html += '<th style="padding: 10px; text-align: center; border: 1px solid #ddd;">قیمت واحد</th>'
        items_html += '<th style="padding: 10px; text-align: center; border: 1px solid #ddd;">جمع</th>'
        items_html += '</tr></thead><tbody>'

        for item in obj.items.all():
            items_html += '<tr style="border-bottom: 1px solid #ddd;">'
            items_html += f'<td style="padding: 10px; border: 1px solid #ddd;">{item.product.title}</td>'
            items_html += f'<td style="padding: 10px; text-align: center; border: 1px solid #ddd;">{item.quantity}</td>'
            items_html += f'<td style="padding: 10px; text-align: center; border: 1px solid #ddd;">{item.price:,} تومان</td>'
            items_html += f'<td style="padding: 10px; text-align: center; border: 1px solid #ddd; font-weight: bold;">{item.get_subtotal():,} تومان</td>'
            items_html += '</tr>'

        items_html += '</tbody></table></div>'
        return mark_safe(items_html)

    get_items_display.short_description = 'محصولات سفارش'

    # Admin Actions
    def confirm_orders(self, request, queryset):
        """Confirm orders after checking transaction"""
        count = 0
        for order in queryset.filter(status='purchased'):
            order.status = 'confirmed'
            order.confirmed_at = timezone.now()
            order.save()
            count += 1

            # Send Telegram notification
            send_telegram_notification(order, action='confirmed')

        self.message_user(request, f'{count} سفارش تایید شد.')

    confirm_orders.short_description = 'تایید سفارش‌های انتخاب شده'

    def mark_as_processing(self, request, queryset):
        queryset.update(status='processing')
        self.message_user(request, 'وضعیت سفارش‌ها به "در حال آماده‌سازی" تغییر یافت.')

    mark_as_processing.short_description = 'تغییر به "در حال آماده‌سازی"'

    def mark_as_shipped(self, request, queryset):
        queryset.update(status='shipped')
        self.message_user(request, 'وضعیت سفارش‌ها به "ارسال شده" تغییر یافت.')

    mark_as_shipped.short_description = 'تغییر به "ارسال شده"'

    def mark_as_delivered(self, request, queryset):
        queryset.update(status='delivered')
        self.message_user(request, 'وضعیت سفارش‌ها به "تحویل داده شده" تغییر یافت.')

    mark_as_delivered.short_description = 'تغییر به "تحویل داده شده"'


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'is_published', 'views', 'published_at']
    list_filter = ['is_published', 'created_at', 'published_at']
    search_fields = ['title', 'content', 'excerpt']
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ['views', 'created_at', 'updated_at']

    fieldsets = (
        ('محتوا', {
            'fields': ('title', 'slug', 'excerpt', 'content', 'featured_image')
        }),
        ('تنظیمات انتشار', {
            'fields': ('author', 'is_published', 'published_at')
        }),
        ('آمار', {
            'fields': ('views', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ('اطلاعات بانکی', {
            'fields': ('card_number', 'card_holder_name', 'bank_name')
        }),
        ('اطلاعات تماس', {
            'fields': ('contact_phone', 'contact_email', 'address')
        }),
        ('تنظیمات تلگرام', {
            'fields': ('telegram_bot_token', 'telegram_chat_id'),
            'description': 'برای دریافت اعلان سفارش‌های جدید در تلگرام'
        }),
    )

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False