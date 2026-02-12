from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, TemplateView
from django.contrib import messages
from django.utils import timezone
from decimal import Decimal
from .models import Product, Order, OrderItem, SiteSettings, BlogPost
from .forms import OrderForm, TransactionForm, OrderTrackingForm
from .utils import send_telegram_notification


# ========== STATIC PAGES ==========

class HomeView(TemplateView):
    template_name = 'website/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['featured_products'] = Product.objects.filter(is_active=True)[:6]
        context['recent_blogs'] = BlogPost.objects.filter(is_published=True)[:3]
        return context


class AboutView(TemplateView):
    template_name = 'website/about.html'


class ContactView(TemplateView):
    template_name = 'website/contact.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            context['settings'] = SiteSettings.objects.first()
        except:
            pass
        return context


# ========== BLOG / MAGAZINE ==========

class MagazineView(ListView):
    model = BlogPost
    template_name = 'website/magazine.html'
    context_object_name = 'blog_posts'
    paginate_by = 9

    def get_queryset(self):
        return BlogPost.objects.filter(is_published=True)


class BlogDetailView(DetailView):
    model = BlogPost
    template_name = 'website/blog_detail.html'
    context_object_name = 'post'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def get_queryset(self):
        return BlogPost.objects.filter(is_published=True)

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        # Increment views
        obj.views += 1
        obj.save(update_fields=['views'])
        return obj


# ========== PRODUCT PAGES ==========

class ProductListView(ListView):
    model = Product
    template_name = 'website/products_list.html'
    context_object_name = 'products'
    paginate_by = 12

    def get_queryset(self):
        queryset = Product.objects.filter(is_active=True)
        category = self.request.GET.get('category')
        if category in ['coffee', 'chocolate']:
            queryset = queryset.filter(category=category)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['selected_category'] = self.request.GET.get('category', 'all')
        return context


class ProductDetailView(DetailView):
    model = Product
    template_name = 'website/product_detail.html'
    context_object_name = 'product'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'


# ========== CART & CHECKOUT ==========

def get_cart(request):
    """Helper function to get cart from session"""
    return request.session.get('cart', {})


def save_cart(request, cart):
    """Helper function to save cart to session"""
    request.session['cart'] = cart
    request.session.modified = True


def add_to_cart(request, product_id):
    """Add product to cart"""
    product = get_object_or_404(Product, id=product_id, is_active=True)
    cart = get_cart(request)

    product_id_str = str(product_id)
    if product_id_str in cart:
        cart[product_id_str]['quantity'] += 1
    else:
        cart[product_id_str] = {
            'title': product.title,
            'price': float(product.price),
            'quantity': 1,
            'main_image': product.main_image.url if product.main_image else None
        }

    save_cart(request, cart)
    messages.success(request, f'{product.title} به سبد خرید اضافه شد')

    return redirect(request.META.get('HTTP_REFERER', 'website:products'))


def update_cart(request, product_id):
    """Update quantity in cart"""
    cart = get_cart(request)
    product_id_str = str(product_id)

    if product_id_str in cart:
        action = request.POST.get('action')
        if action == 'increase':
            cart[product_id_str]['quantity'] += 1
        elif action == 'decrease':
            if cart[product_id_str]['quantity'] > 1:
                cart[product_id_str]['quantity'] -= 1
            else:
                del cart[product_id_str]

        save_cart(request, cart)

    return redirect('website:cart')


def remove_from_cart(request, product_id):
    """Remove product from cart"""
    cart = get_cart(request)
    product_id_str = str(product_id)

    if product_id_str in cart:
        del cart[product_id_str]
        save_cart(request, cart)
        messages.success(request, 'محصول از سبد خرید حذف شد')

    return redirect('website:cart')


def cart_view(request):
    """Display cart and checkout form"""
    cart = get_cart(request)

    if not cart:
        return render(request, 'website/cart.html', {'cart': {}, 'total': 0})

    # Calculate total
    total = sum(item['price'] * item['quantity'] for item in cart.values())

    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            # Create order
            order = form.save(commit=False)
            order.total_price = Decimal(str(total))
            order.status = 'pending'
            order.save()

            # Create order items
            for product_id, item in cart.items():
                product = Product.objects.get(id=int(product_id))
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=item['quantity'],
                    price=Decimal(str(item['price']))
                )

            # Clear cart
            request.session['cart'] = {}
            request.session['order_id'] = order.id

            return redirect('website:order_confirmation')
    else:
        form = OrderForm()

    context = {
        'cart': cart,
        'total': total,
        'form': form
    }

    return render(request, 'website/cart.html', context)


def order_confirmation(request):
    """Show payment details and accept transaction ID"""
    order_id = request.session.get('order_id')
    if not order_id:
        return redirect('website:home')

    order = get_object_or_404(Order, id=order_id)
    settings = SiteSettings.objects.first()

    if request.method == 'POST':
        form = TransactionForm(request.POST)
        if form.is_valid():
            order.transaction_id = form.cleaned_data['transaction_id']
            order.status = 'purchased'
            order.purchased_at = timezone.now()
            order.save()

            # Send Telegram notification
            send_telegram_notification(order, action='new_order')

            # Clear session
            if 'order_id' in request.session:
                del request.session['order_id']

            messages.success(request, 'سفارش شما با موفقیت ثبت شد! کد پیگیری خود را یادداشت کنید.')
            return redirect('website:order_success', tracking_code=order.tracking_code)
    else:
        form = TransactionForm()

    context = {
        'order': order,
        'settings': settings,
        'form': form
    }

    return render(request, 'website/order_confirmation.html', context)


def order_success(request, tracking_code):
    """Order success page"""
    order = get_object_or_404(Order, tracking_code=tracking_code)
    return render(request, 'website/order_success.html', {'order': order})


# ========== ORDER TRACKING ==========

def order_tracking(request):
    """Track order by phone number and tracking code"""
    order = None

    if request.method == 'POST':
        form = OrderTrackingForm(request.POST)
        if form.is_valid():
            phone = form.cleaned_data['phone_number']
            tracking_code = form.cleaned_data['tracking_code']

            try:
                order = Order.objects.get(
                    phone_number=phone,
                    tracking_code=tracking_code
                )
            except Order.DoesNotExist:
                messages.error(request, 'سفارشی با این مشخصات یافت نشد.')
    else:
        form = OrderTrackingForm()

    context = {
        'form': form,
        'order': order
    }

    return render(request, 'website/order_tracking.html', context)