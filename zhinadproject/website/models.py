from django.db import models
from django.core.validators import RegexValidator
from django.utils.text import slugify
from django.utils import timezone
from django.core.exceptions import ValidationError
import secrets
from django.utils.safestring import mark_safe

try:
    import bleach
except Exception:  # pragma: no cover
    bleach = None


class Category(models.Model):
    title = models.CharField(max_length=200, unique=True, verbose_name='عنوان')
    slug = models.SlugField(max_length=200, unique=True, blank=True, verbose_name='نامک')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاریخ بروزرسانی')

    class Meta:
        verbose_name = 'دسته‌بندی'
        verbose_name_plural = 'دسته‌بندی‌ها'
        ordering = ['title']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title, allow_unicode=True)
        super().save(*args, **kwargs)


class Tag(models.Model):
    title = models.CharField(max_length=200, unique=True, verbose_name='عنوان')
    slug = models.SlugField(max_length=200, unique=True, blank=True, verbose_name='نامک')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاریخ بروزرسانی')

    class Meta:
        verbose_name = 'برچسب'
        verbose_name_plural = 'برچسب‌ها'
        ordering = ['title']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title, allow_unicode=True)
        super().save(*args, **kwargs)


class Product(models.Model):
    """Model for Coffee and Chocolate Products"""

    title = models.CharField(max_length=200, verbose_name='عنوان')
    slug = models.SlugField(max_length=200, unique=True, blank=True, verbose_name='نامک')
    subtitle = models.CharField(max_length=300, blank=True, verbose_name='زیرعنوان')
    description = models.TextField(verbose_name='توضیحات')
    category = models.ForeignKey(
        Category,
        related_name='products',
        on_delete=models.PROTECT,
        verbose_name='دسته‌بندی',
    )
    tags = models.ManyToManyField(
        Tag,
        related_name='products',
        blank=True,
        verbose_name='برچسب‌ها',
    )

    main_image = models.ImageField(upload_to='products/main/', verbose_name='تصویر اصلی')
    price = models.DecimalField(max_digits=10, decimal_places=0, null=True, blank=True, verbose_name='قیمت (تومان)')

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

    def clean(self):
        super().clean()
        if self.pk and self.tags.count() > 10:
            raise ValidationError({"tags": "حداکثر ۱۰ برچسب قابل انتخاب است."})

    @property
    def is_buyable(self) -> bool:
        return self.is_active and self.stock > 0 and self.price is not None


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
        ('purchased', 'پرداخت شده - در انتظار تایید'),
        ('confirmed', 'تایید شده'),
        ('processing', 'در حال آماده‌سازی'),
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
    tracking_code = models.CharField(max_length=50, blank=True, verbose_name='کد پیگیری سفارش')

    # Payment Information
    card_number = models.CharField(max_length=16, blank=True, verbose_name='شماره کارت پرداخت')
    transaction_id = models.CharField(max_length=100, blank=True, verbose_name='شماره پیگیری تراکنش')

    # Admin Notes
    admin_notes = models.TextField(blank=True, verbose_name='یادداشت ادمین')

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاریخ بروزرسانی')
    purchased_at = models.DateTimeField(null=True, blank=True, verbose_name='تاریخ پرداخت')
    confirmed_at = models.DateTimeField(null=True, blank=True, verbose_name='تاریخ تایید')

    # Telegram notification sent
    telegram_notified = models.BooleanField(default=False, verbose_name='اعلان تلگرام ارسال شده')

    class Meta:
        verbose_name = 'سفارش'
        verbose_name_plural = 'سفارشات'
        ordering = ['-created_at']

    def __str__(self):
        return f"سفارش #{self.id} - {self.customer_name}"

    def get_total_items(self):
        return sum(item.quantity for item in self.items.all())

    def save(self, *args, **kwargs):
        if not self.tracking_code:
            # Short, readable, non-incremental tracking code (collision-checked)
            alphabet = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"  # no 0/O, 1/I/L
            while True:
                part1 = "".join(secrets.choice(alphabet) for _ in range(4))
                part2 = "".join(secrets.choice(alphabet) for _ in range(4))
                code = f"ZH-{part1}-{part2}"
                if not Order.objects.filter(tracking_code=code).exists():
                    self.tracking_code = code
                    break
        super().save(*args, **kwargs)


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


class BlogPost(models.Model):
    """Blog posts for Magazine section"""
    title = models.CharField(max_length=200, verbose_name='عنوان')
    slug = models.SlugField(max_length=200, unique=True, blank=True, verbose_name='نامک')
    excerpt = models.TextField(max_length=300, verbose_name='خلاصه مطلب')
    content = models.TextField(verbose_name='محتوا')

    featured_image = models.ImageField(upload_to='blog/', verbose_name='تصویر شاخص')

    author = models.CharField(max_length=100, default='تیم ژیناد', verbose_name='نویسنده')

    is_published = models.BooleanField(default=True, verbose_name='منتشر شده')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاریخ بروزرسانی')
    published_at = models.DateTimeField(default=timezone.now, verbose_name='تاریخ انتشار')

    views = models.IntegerField(default=0, verbose_name='تعداد بازدید')

    class Meta:
        verbose_name = 'مقاله'
        verbose_name_plural = 'مقالات مجله'
        ordering = ['-published_at']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title, allow_unicode=True)
        super().save(*args, **kwargs)


class ContentPage(models.Model):
    PAGE_TYPE_CHOICES = [
        ("about", "درباره ما"),
        ("contact", "تماس با ما"),
        ("blog_post", "پست مجله"),
    ]

    page_type = models.CharField(max_length=20, choices=PAGE_TYPE_CHOICES, verbose_name="نوع صفحه")
    title = models.CharField(max_length=200, verbose_name="عنوان")
    slug = models.SlugField(max_length=200, unique=True, blank=True, verbose_name="نامک")

    # Blog-like fields (used when page_type == blog_post)
    excerpt = models.TextField(max_length=300, blank=True, verbose_name="خلاصه")
    featured_image = models.ImageField(upload_to="content/featured/", blank=True, null=True, verbose_name="تصویر شاخص")
    author = models.CharField(max_length=100, blank=True, default="تیم ژیناد", verbose_name="نویسنده")
    is_published = models.BooleanField(default=True, verbose_name="منتشر شده")
    published_at = models.DateTimeField(default=timezone.now, verbose_name="تاریخ انتشار")
    views = models.IntegerField(default=0, verbose_name="تعداد بازدید")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")

    class Meta:
        verbose_name = "صفحه محتوا"
        verbose_name_plural = "صفحات محتوا"
        ordering = ["-published_at", "-created_at"]

    def __str__(self):
        return f"{self.get_page_type_display()}: {self.title}"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title, allow_unicode=True)
        super().save(*args, **kwargs)


class ContentBlock(models.Model):
    BLOCK_TYPE_CHOICES = [
        ("heading", "عنوان"),
        ("rich_html", "متن (HTML)"),
        ("image", "تصویر"),
        ("callout", "کادر برجسته"),
        ("divider", "جداکننده"),
    ]

    page = models.ForeignKey(ContentPage, related_name="blocks", on_delete=models.CASCADE, verbose_name="صفحه")
    parent = models.ForeignKey(
        "self",
        related_name="children",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="والد",
    )
    order = models.PositiveIntegerField(default=0, verbose_name="ترتیب")

    block_type = models.CharField(max_length=20, choices=BLOCK_TYPE_CHOICES, verbose_name="نوع بلاک")
    title = models.CharField(max_length=200, blank=True, verbose_name="عنوان")
    body_html = models.TextField(blank=True, verbose_name="محتوا (HTML)")
    image = models.ImageField(upload_to="content/blocks/", blank=True, null=True, verbose_name="تصویر")
    caption = models.CharField(max_length=300, blank=True, verbose_name="کپشن")

    class Meta:
        verbose_name = "بلاک محتوا"
        verbose_name_plural = "بلاک‌های محتوا"
        ordering = ["parent_id", "order", "id"]

    def __str__(self):
        return f"{self.get_block_type_display()} - {self.title or self.id}"

    @staticmethod
    def sanitize_html(value: str) -> str:
        if not value:
            return ""
        if bleach is None:
            # Fail closed: if bleach isn't available, show plain text (no HTML).
            return (
                value.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
            )

        allowed_tags = [
            "p",
            "br",
            "strong",
            "em",
            "ul",
            "ol",
            "li",
            "a",
            "h2",
            "h3",
            "h4",
            "blockquote",
            "hr",
        ]
        allowed_attrs = {
            "a": ["href", "title"],
        }
        cleaned = bleach.clean(
            value,
            tags=allowed_tags,
            attributes=allowed_attrs,
            strip=True,
        )
        return cleaned

    @property
    def body_html_safe(self):
        return mark_safe(self.body_html)

    def save(self, *args, **kwargs):
        if self.parent_id and self.page_id != self.parent.page_id:
            self.page_id = self.parent.page_id
        if self.block_type in ("rich_html", "callout") and self.body_html:
            self.body_html = self.sanitize_html(self.body_html)
        super().save(*args, **kwargs)


class SiteSettings(models.Model):
    """Site-wide settings"""
    card_number = models.CharField(max_length=16, verbose_name='شماره کارت دریافت وجه')
    card_holder_name = models.CharField(max_length=200, verbose_name='نام صاحب کارت')
    bank_name = models.CharField(max_length=100, verbose_name='نام بانک')
    contact_phone = models.CharField(max_length=11, verbose_name='شماره تماس')
    contact_email = models.EmailField(blank=True, verbose_name='ایمیل')
    address = models.TextField(blank=True, verbose_name='آدرس')

    # Branding / Landing images (optional)
    logo_image = models.ImageField(
        upload_to="site/branding/",
        blank=True,
        null=True,
        verbose_name="لوگوی سایت (اختیاری)",
    )
    footer_image = models.ImageField(
        upload_to="site/landing/",
        blank=True,
        null=True,
        verbose_name="تصویر پس‌زمینه فوتر (اختیاری)",
    )

    # Telegram Bot Settings
    telegram_bot_token = models.CharField(max_length=200, blank=True, verbose_name='توکن ربات تلگرام')

    # Bale Bot Settings
    bale_bot_token = models.CharField(max_length=200, blank=True, verbose_name='توکن ربات بله')

    class Meta:
        verbose_name = 'تنظیمات سایت'
        verbose_name_plural = 'تنظیمات سایت'

    def __str__(self):
        return "تنظیمات سایت"


class HomeHeroImage(models.Model):
    settings = models.ForeignKey(
        SiteSettings,
        related_name="hero_images",
        on_delete=models.CASCADE,
        verbose_name="تنظیمات سایت",
    )
    image = models.ImageField(upload_to="site/landing/hero/", verbose_name="تصویر")
    order = models.PositiveIntegerField(default=0, verbose_name="ترتیب")
    is_active = models.BooleanField(default=True, verbose_name="فعال")

    class Meta:
        verbose_name = "تصویر هدر صفحه اصلی"
        verbose_name_plural = "تصاویر هدر صفحه اصلی"
        ordering = ["order", "id"]

    def __str__(self):
        return f"Hero image #{self.id}"


class NotificationRecipient(models.Model):
    """Recipients for order notifications"""
    PLATFORM_CHOICES = [
        ('telegram', 'تلگرام'),
        ('bale', 'بله'),
    ]

    name = models.CharField(max_length=200, verbose_name='نام گیرنده')
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES, verbose_name='پلتفرم')
    chat_id = models.CharField(max_length=100, verbose_name='شناسه چت')
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاریخ بروزرسانی')

    class Meta:
        verbose_name = 'گیرنده اعلان'
        verbose_name_plural = 'گیرندگان اعلان'
        ordering = ['platform', 'name']

    def __str__(self):
        status = "فعال" if self.is_active else "غیرفعال"
        return f"{self.name} ({self.get_platform_display()}) - {status}"