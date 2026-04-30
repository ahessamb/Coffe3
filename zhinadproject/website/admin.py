from django.contrib import admin
from django import forms
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from django.utils.safestring import mark_safe
import nested_admin
from tinymce.widgets import TinyMCE
from .models import (
    Category,
    Tag,
    Product,
    ProductImage,
    Order,
    OrderItem,
    SiteSettings,
    HomeHeroImage,
    BlogPost,
    ContentPage,
    ContentBlock,
    NotificationRecipient,
)
from .utils import send_all_notifications


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ['image', 'alt_text', 'order']


class ProductAdminForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = "__all__"

    def clean_tags(self):
        tags = self.cleaned_data.get("tags")
        if tags is not None and tags.count() > 10:
            raise forms.ValidationError("حداکثر ۱۰ برچسب قابل انتخاب است.")
        return tags


class ContentBlockForm(forms.ModelForm):
    body_html = forms.CharField(required=False, widget=TinyMCE())

    class Meta:
        model = ContentBlock
        fields = "__all__"


class ChildContentBlockInline(nested_admin.NestedStackedInline):
    model = ContentBlock
    form = ContentBlockForm
    fk_name = "parent"
    extra = 0
    sortable_field_name = "order"
    fields = ("order", "block_type", "title", "body_html", "image", "caption")


class ContentBlockInline(nested_admin.NestedStackedInline):
    model = ContentBlock
    form = ContentBlockForm
    fk_name = "page"
    extra = 0
    sortable_field_name = "order"
    fields = ("order", "block_type", "title", "body_html", "image", "caption")
    inlines = [ChildContentBlockInline]

    def get_queryset(self, request):
        # Only show top-level blocks; children are managed nested under parents.
        return super().get_queryset(request).filter(parent__isnull=True)


@admin.register(ContentPage)
class ContentPageAdmin(nested_admin.NestedModelAdmin):
    list_display = ("title", "page_type", "slug", "is_published", "published_at", "updated_at")
    list_filter = ("page_type", "is_published")
    search_fields = ("title", "slug", "excerpt")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [ContentBlockInline]

    fieldsets = (
        ("اطلاعات صفحه", {"fields": ("page_type", "title", "slug", "is_published")}),
        (
            "ویژگی‌های مجله (برای پست‌ها)",
            {"fields": ("excerpt", "featured_image", "author", "published_at", "views")},
        ),
        ("زمان‌ها", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )
    readonly_fields = ("created_at", "updated_at", "views")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["title", "slug", "product_count", "products_link"]
    search_fields = ["title", "slug"]
    prepopulated_fields = {"slug": ("title",)}

    def product_count(self, obj):
        return obj.products.count()

    product_count.short_description = "تعداد محصولات"

    def products_link(self, obj):
        url = reverse("admin:website_product_changelist")
        return format_html('<a href="{}?category__id__exact={}">مشاهده محصولات</a>', url, obj.id)

    products_link.short_description = "محصولات"

    def has_delete_permission(self, request, obj=None):
        if obj is not None and obj.products.exists():
            return False
        return super().has_delete_permission(request, obj=obj)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ["title", "slug", "product_count", "products_link"]
    search_fields = ["title", "slug"]
    prepopulated_fields = {"slug": ("title",)}

    def product_count(self, obj):
        return obj.products.count()

    product_count.short_description = "تعداد محصولات"

    def products_link(self, obj):
        url = reverse("admin:website_product_changelist")
        return format_html('<a href="{}?tags__id__exact={}">مشاهده محصولات</a>', url, obj.id)

    products_link.short_description = "محصولات"

    def has_delete_permission(self, request, obj=None):
        if obj is not None and obj.products.exists():
            return False
        return super().has_delete_permission(request, obj=obj)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    form = ProductAdminForm
    list_display = ['title', 'category', 'price', 'stock', 'is_active', 'created_at']
    list_filter = ['category', 'tags', 'is_active', 'created_at']
    search_fields = ['title', 'description']
    prepopulated_fields = {'slug': ('title',)}
    inlines = [ProductImageInline]

    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('title', 'slug', 'subtitle', 'category', 'tags')
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
    actions = [
        'confirm_orders',
        'mark_as_processing',
        'mark_as_shipped',
        'mark_as_delivered',
        'mark_as_cancelled'
    ]

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

            # Send notifications to both Telegram and Bale
            send_all_notifications(order, action='confirmed')

        self.message_user(request, f'{count} سفارش تایید شد.')

    confirm_orders.short_description = 'تایید سفارش‌های انتخاب شده'

    def mark_as_processing(self, request, queryset):
        count = queryset.update(status='processing')

        # Send notifications
        for order in queryset:
            send_all_notifications(order, action='processing')

        self.message_user(request, f'وضعیت {count} سفارش به "در حال آماده‌سازی" تغییر یافت.')

    mark_as_processing.short_description = 'تغییر به "در حال آماده‌سازی"'

    def mark_as_shipped(self, request, queryset):
        count = queryset.update(status='shipped')

        # Send notifications
        for order in queryset:
            send_all_notifications(order, action='shipped')

        self.message_user(request, f'وضعیت {count} سفارش به "ارسال شده" تغییر یافت.')

    mark_as_shipped.short_description = 'تغییر به "ارسال شده"'

    def mark_as_delivered(self, request, queryset):
        count = queryset.update(status='delivered')

        # Send notifications
        for order in queryset:
            send_all_notifications(order, action='delivered')

        self.message_user(request, f'وضعیت {count} سفارش به "تحویل داده شده" تغییر یافت.')

    mark_as_delivered.short_description = 'تغییر به "تحویل داده شده"'

    def mark_as_cancelled(self, request, queryset):
        count = queryset.update(status='cancelled')

        # Send notifications
        for order in queryset:
            send_all_notifications(order, action='cancelled')

        self.message_user(request, f'وضعیت {count} سفارش به "لغو شده" تغییر یافت.')

    mark_as_cancelled.short_description = 'تغییر به "لغو شده"'


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
    class HomeHeroImageInline(admin.TabularInline):
        model = HomeHeroImage
        extra = 1
        fields = ("image", "order", "is_active")
        ordering = ("order",)

    fieldsets = (
        ("تصاویر و برندینگ", {"fields": ("logo_image", "footer_image")}),
        ('اطلاعات بانکی', {
            'fields': ('card_number', 'card_holder_name', 'bank_name')
        }),
        ('اطلاعات تماس', {
            'fields': ('contact_phone', 'contact_email', 'address', 'address_lat', 'address_lng')
        }),
        ('تنظیمات تلگرام', {
            'fields': ('telegram_bot_token',),
            'description': 'توکن ربات تلگرام برای ارسال اعلان‌ها'
        }),
        ('تنظیمات بله', {
            'fields': ('bale_bot_token',),
            'description': 'توکن ربات بله برای ارسال اعلان‌ها'
        }),
    )
    inlines = [HomeHeroImageInline]

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(NotificationRecipient)
class NotificationRecipientAdmin(admin.ModelAdmin):
    list_display = ['name', 'platform', 'chat_id', 'is_active_display', 'created_at']
    list_filter = ['platform', 'is_active', 'created_at']
    search_fields = ['name', 'chat_id']

    fieldsets = (
        ('اطلاعات گیرنده', {
            'fields': ('name', 'platform', 'chat_id')
        }),
        ('وضعیت', {
            'fields': ('is_active',)
        }),
    )

    def is_active_display(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="background-color: #4CAF50; color: white; padding: 5px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
                'فعال'
            )
        else:
            return format_html(
                '<span style="background-color: #F44336; color: white; padding: 5px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
                'غیرفعال'
            )

    is_active_display.short_description = 'وضعیت'

    actions = ['activate_recipients', 'deactivate_recipients']

    def activate_recipients(self, request, queryset):
        count = queryset.update(is_active=True)
        self.message_user(request, f'{count} گیرنده فعال شد.')

    activate_recipients.short_description = 'فعال کردن گیرندگان انتخاب شده'

    def deactivate_recipients(self, request, queryset):
        count = queryset.update(is_active=False)
        self.message_user(request, f'{count} گیرنده غیرفعال شد.')

    deactivate_recipients.short_description = 'غیرفعال کردن گیرندگان انتخاب شده'