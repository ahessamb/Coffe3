from django.contrib import admin
from .models import Product, ProductImage, Order, OrderItem, SiteSettings


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
        return f"{obj.get_subtotal():,} تومان"

    get_subtotal.short_description = 'جمع'


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'customer_name', 'phone_number', 'status', 'total_price', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['customer_name', 'phone_number', 'transaction_id']
    readonly_fields = ['created_at', 'updated_at', 'total_price']
    inlines = [OrderItemInline]

    fieldsets = (
        ('اطلاعات مشتری', {
            'fields': ('customer_name', 'phone_number', 'phone_number_2', 'address', 'additional_notes')
        }),
        ('اطلاعات سفارش', {
            'fields': ('status', 'total_price', 'created_at', 'updated_at')
        }),
        ('اطلاعات پرداخت', {
            'fields': ('card_number', 'transaction_id', 'purchased_at')
        }),
    )

    def get_queryset(self, request):
        # Show all orders except drafts in admin
        qs = super().get_queryset(request)
        return qs.exclude(status='draft')


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        # Only allow one settings object
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False