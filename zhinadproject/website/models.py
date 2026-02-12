from django.db import models
from django.core.validators import RegexValidator
from django.utils.text import slugify


class Product(models.Model):
    """Model for Coffee and Chocolate Products"""
    CATEGORY_CHOICES = [
        ('coffee', 'قهوه'),
        ('chocolate', 'شکلات'),
    ]

    title = models.CharField(max_length=200, verbose_name='عنوان')
    slug = models.SlugField(max_length=200, unique=True, blank=True, verbose_name='نامک')
    subtitle = models.CharField(max_length=300, blank=True, verbose_name='زیرعنوان')
    description = models.TextField(verbose_name='توضیحات')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, verbose_name='دسته‌بندی')

    main_image = models.ImageField(upload_to='products/main/', verbose_name='تصویر اصلی')
    price = models.DecimalField(max_digits=10, decimal_places=0, verbose_name='قیمت (تومان)')

    is_active = models.BooleanField(default=True, verbose_name='فعال')
    stock = models.IntegerField(default=0, verbose_name='موجودی')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاریخ بروزرسانی')

    class Meta:
        verbose_name = 'محصول'
        verbose_name_plural = 'محصولات'
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title, allow_unicode=True)
        super().save(*args, **kwargs)


class ProductImage(models.Model):
    """Additional images for products"""
    product = models.ForeignKey(Product, related_name='images', on_delete=models.CASCADE, verbose_name='محصول')
    image = models.ImageField(upload_to='products/gallery/', verbose_name='تصویر')
    alt_text = models.CharField(max_length=200, blank=True, verbose_name='متن جایگزین')
    order = models.IntegerField(default=0, verbose_name='ترتیب')

    class Meta:
        verbose_name = 'تصویر محصول'
        verbose_name_plural = 'تصاویر محصولات'
        ordering = ['order']

    def __str__(self):
        return f"{self.product.title} - تصویر {self.order}"


class Order(models.Model):
    """Customer Orders"""
    STATUS_CHOICES = [
        ('draft', 'پیش‌نویس'),
        ('pending', 'در انتظار پرداخت'),
        ('purchased', 'پرداخت شده'),
        ('processing', 'در حال پردازش'),
        ('shipped', 'ارسال شده'),
        ('delivered', 'تحویل داده شده'),
        ('cancelled', 'لغو شده'),
    ]

    # Customer Information
    customer_name = models.CharField(max_length=200, verbose_name='نام و نام خانوادگی')
    phone_regex = RegexValidator(regex=r'^09\d{9}$', message="شماره تلفن باید به فرمت 09xxxxxxxxx باشد")
    phone_number = models.CharField(validators=[phone_regex], max_length=11, verbose_name='شماره تماس')
    phone_number_2 = models.CharField(max_length=11, blank=True, verbose_name='شماره تماس دوم')
    address = models.TextField(verbose_name='آدرس')
    additional_notes = models.TextField(blank=True, verbose_name='یادداشت‌های اضافی')

    # Order Information
    total_price = models.DecimalField(max_digits=12, decimal_places=0, verbose_name='مبلغ کل')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name='وضعیت')

    # Payment Information
    card_number = models.CharField(max_length=16, blank=True, verbose_name='شماره کارت پرداخت')
    transaction_id = models.CharField(max_length=100, blank=True, verbose_name='شماره پیگیری')

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاریخ بروزرسانی')
    purchased_at = models.DateTimeField(null=True, blank=True, verbose_name='تاریخ پرداخت')

    class Meta:
        verbose_name = 'سفارش'
        verbose_name_plural = 'سفارشات'
        ordering = ['-created_at']

    def __str__(self):
        return f"سفارش #{self.id} - {self.customer_name}"

    def get_total_items(self):
        return sum(item.quantity for item in self.items.all())


class OrderItem(models.Model):
    """Items in an order"""
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE, verbose_name='سفارش')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, verbose_name='محصول')
    quantity = models.PositiveIntegerField(default=1, verbose_name='تعداد')
    price = models.DecimalField(max_digits=10, decimal_places=0, verbose_name='قیمت واحد')

    class Meta:
        verbose_name = 'آیتم سفارش'
        verbose_name_plural = 'آیتم‌های سفارش'

    def __str__(self):
        return f"{self.product.title} x {self.quantity}"

    def get_subtotal(self):
        return self.price * self.quantity


class SiteSettings(models.Model):
    """Site-wide settings for card number, etc."""
    card_number = models.CharField(max_length=16, verbose_name='شماره کارت دریافت وجه')
    card_holder_name = models.CharField(max_length=200, verbose_name='نام صاحب کارت')
    bank_name = models.CharField(max_length=100, verbose_name='نام بانک')
    contact_phone = models.CharField(max_length=11, verbose_name='شماره تماس')
    contact_email = models.EmailField(blank=True, verbose_name='ایمیل')
    address = models.TextField(blank=True, verbose_name='آدرس')

    class Meta:
        verbose_name = 'تنظیمات سایت'
        verbose_name_plural = 'تنظیمات سایت'

    def __str__(self):
        return "تنظیمات سایت"