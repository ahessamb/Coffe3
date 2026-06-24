from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, TemplateView
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import F
from decimal import Decimal
from .models import Category, Tag, Product, Order, OrderItem, BlogPost, ContentPage
from .forms import OrderForm, OrderTrackingForm
from .utils import schedule_order_notifications
from .seo import article_json_ld, product_json_ld


# ========== STATIC PAGES ==========

class HomeView(TemplateView):
    template_name = 'website/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['featured_products'] = Product.objects.filter(is_active=True)[:6]
        context['recent_blogs'] = ContentPage.objects.filter(page_type="blog_post", is_published=True).order_by("-published_at")[:3]
        return context


class AboutView(TemplateView):
    template_name = "website/content_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        page = get_object_or_404(ContentPage, page_type="about", slug="about", is_published=True)
        blocks = (
            page.blocks.filter(parent__isnull=True)
            .prefetch_related("children", "children__children")
            .order_by("order", "id")
        )
        context["page"] = page
        context["blocks"] = blocks
        return context


class ContactView(TemplateView):
    template_name = "website/content_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        page = get_object_or_404(ContentPage, page_type="contact", slug="contact", is_published=True)
        blocks = (
            page.blocks.filter(parent__isnull=True)
            .prefetch_related("children", "children__children")
            .order_by("order", "id")
        )
        context["page"] = page
        context["blocks"] = blocks
        return context


class LocationView(TemplateView):
    template_name = "website/location.html"


# ========== BLOG / MAGAZINE ==========

class MagazineView(ListView):
    model = ContentPage
    template_name = "website/blog_list.html"
    context_object_name = 'blog_posts'
    paginate_by = 9

    def get_queryset(self):
        return ContentPage.objects.filter(page_type="blog_post", is_published=True).order_by("-published_at")


class BlogDetailView(DetailView):
    model = ContentPage
    template_name = "website/blog_detail_cms.html"
    context_object_name = "page"
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def get_queryset(self):
        return ContentPage.objects.filter(page_type="blog_post", is_published=True)

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        # Increment views
        obj.views += 1
        obj.save(update_fields=['views'])
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        page = context["page"]
        blocks = (
            page.blocks.filter(parent__isnull=True)
            .prefetch_related("children", "children__children")
            .order_by("order", "id")
        )
        context["blocks"] = blocks
        context["article_json_ld"] = article_json_ld(page)
        return context


# ========== PRODUCT PAGES ==========

class ProductListView(ListView):
    model = Product
    template_name = 'website/products_list.html'
    context_object_name = 'products'
    paginate_by = 12

    def get_queryset(self):
        queryset = (
            Product.objects.filter(is_active=True)
            .select_related("category")
            .prefetch_related("tags")
        )

        category_slug = self.request.GET.get("category")
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)

        tag_slugs = [t for t in self.request.GET.getlist("tag") if t]
        if tag_slugs:
            queryset = queryset.filter(tags__slug__in=tag_slugs).distinct()

        min_price = self.request.GET.get("min_price")
        max_price = self.request.GET.get("max_price")
        if min_price:
            queryset = queryset.filter(price__isnull=False, price__gte=min_price)
        if max_price:
            queryset = queryset.filter(price__isnull=False, price__lte=max_price)

        sort = self.request.GET.get("sort") or "newest"
        if sort == "price_asc":
            queryset = queryset.order_by(F("price").asc(nulls_last=True), "-created_at")
        elif sort == "price_desc":
            queryset = queryset.order_by(F("price").desc(nulls_last=True), "-created_at")
        elif sort == "oldest":
            queryset = queryset.order_by("created_at")
        else:  # newest
            queryset = queryset.order_by("-created_at")

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categories"] = Category.objects.all().order_by("title")
        context["tags"] = Tag.objects.all().order_by("title")
        context["selected_category"] = self.request.GET.get("category", "")
        context["selected_tags"] = [t for t in self.request.GET.getlist("tag") if t]
        context["sort"] = self.request.GET.get("sort") or "newest"
        context["min_price"] = self.request.GET.get("min_price", "")
        context["max_price"] = self.request.GET.get("max_price", "")
        return context


class ProductDetailView(DetailView):
    model = Product
    template_name = 'website/product_detail.html'
    context_object_name = 'product'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["product_json_ld"] = product_json_ld(context["product"])
        return context


# ========== CART & CHECKOUT ==========

def get_cart(request):
    """Helper function to get cart from session"""
    return request.session.get('cart', {})


def save_cart(request, cart):
    """Helper function to save cart to session"""
    request.session['cart'] = cart
    request.session.modified = True


def is_ajax_request(request):
    return request.headers.get('X-Requested-With') == 'XMLHttpRequest'


def build_cleaned_cart(cart, products_by_id=None):
    """Validate cart items against current products and compute totals."""
    if not cart:
        return {}, Decimal("0"), {}

    if products_by_id is None:
        product_ids = [int(pid) for pid in cart.keys()]
        products_by_id = {
            p.id: p for p in Product.objects.filter(id__in=product_ids, is_active=True).select_related("category")
        }

    cleaned_cart = {}
    total = Decimal("0")
    for pid_str, item in cart.items():
        pid = int(pid_str)
        product = products_by_id.get(pid)
        if not product or product.price is None or product.stock <= 0:
            continue

        qty = int(item.get("quantity", 1))
        qty = max(1, min(qty, int(product.stock)))
        unit_price = Decimal(str(product.price))
        subtotal = unit_price * qty

        cleaned_cart[pid_str] = {
            **item,
            "price": float(product.price),
            "quantity": qty,
            "max_quantity": int(product.stock),
            "subtotal": float(subtotal),
        }
        total += subtotal

    return cleaned_cart, total, products_by_id


def cart_json_payload(cleaned_cart, total, product_id=None, removed=False):
    items = {
        pid: {
            "quantity": item["quantity"],
            "subtotal": item["subtotal"],
            "price": item["price"],
        }
        for pid, item in cleaned_cart.items()
    }
    total_quantity = sum(item["quantity"] for item in cleaned_cart.values())
    payload = {
        "success": True,
        "cart_count": len(cleaned_cart),
        "total_quantity": total_quantity,
        "total": float(total),
        "items": items,
        "removed": removed,
    }
    if product_id is not None:
        pid_str = str(product_id)
        if removed or pid_str not in cleaned_cart:
            payload["item"] = None
        else:
            item = cleaned_cart[pid_str]
            payload["item"] = {
                "quantity": item["quantity"],
                "subtotal": item["subtotal"],
                "price": item["price"],
            }
    return payload


def add_to_cart(request, product_id):
    """Add product to cart"""
    product = get_object_or_404(Product, id=product_id, is_active=True)
    ajax = is_ajax_request(request)

    if product.price is None:
        message = "این محصول قیمت ندارد. برای اطلاع از آخرین قیمت تماس بگیرید."
        if ajax:
            return JsonResponse({"success": False, "message": message}, status=400)
        messages.error(request, message)
        return redirect(request.META.get("HTTP_REFERER", "website:products"))
    if product.stock <= 0:
        message = "این محصول موجود نیست."
        if ajax:
            return JsonResponse({"success": False, "message": message}, status=400)
        messages.error(request, message)
        return redirect(request.META.get("HTTP_REFERER", "website:products"))

    cart = get_cart(request)

    product_id_str = str(product_id)
    try:
        requested_qty = int(request.POST.get("quantity", 1))
    except (TypeError, ValueError):
        requested_qty = 1
    requested_qty = max(1, min(requested_qty, int(product.stock)))

    if product_id_str in cart:
        cart[product_id_str]["quantity"] = min(
            int(product.stock),
            int(cart[product_id_str].get("quantity", 0)) + requested_qty,
        )
    else:
        cart[product_id_str] = {
            'title': product.title,
            'price': float(product.price),
            'quantity': requested_qty,
            'main_image': product.main_image.url if product.main_image else None
        }

    save_cart(request, cart)
    success_message = f'{product.title} به سبد خرید اضافه شد'

    if ajax:
        cleaned_cart, total, _ = build_cleaned_cart(cart)
        payload = cart_json_payload(cleaned_cart, total)
        payload["message"] = success_message
        return JsonResponse(payload)

    messages.success(request, success_message)
    return redirect(request.META.get('HTTP_REFERER', 'website:products'))


def update_cart(request, product_id):
    """Update quantity in cart"""
    cart = get_cart(request)
    product_id_str = str(product_id)
    ajax = is_ajax_request(request)
    removed = False

    if product_id_str in cart:
        product = get_object_or_404(Product, id=product_id, is_active=True)
        if product.price is None or product.stock <= 0:
            del cart[product_id_str]
            save_cart(request, cart)
            removed = True
            message = "این محصول قابل خرید نیست و از سبد حذف شد."
            if ajax:
                cleaned_cart, total, _ = build_cleaned_cart(cart)
                payload = cart_json_payload(cleaned_cart, total, product_id=product_id, removed=True)
                payload["message"] = message
                return JsonResponse(payload)
            messages.error(request, message)
            return redirect("website:cart")

        action = request.POST.get('action')
        if action == 'increase':
            cart[product_id_str]['quantity'] = min(
                int(product.stock),
                int(cart[product_id_str]['quantity']) + 1
            )
        elif action == 'decrease':
            if cart[product_id_str]['quantity'] > 1:
                cart[product_id_str]['quantity'] -= 1
            else:
                del cart[product_id_str]
                removed = True
        elif action == "set":
            try:
                qty = int(request.POST.get("quantity", 1))
            except (TypeError, ValueError):
                qty = 1
            qty = max(1, min(qty, int(product.stock)))
            cart[product_id_str]["quantity"] = qty

        save_cart(request, cart)

    if ajax:
        cleaned_cart, total, _ = build_cleaned_cart(cart)
        payload = cart_json_payload(cleaned_cart, total, product_id=product_id, removed=removed)
        return JsonResponse(payload)

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
        return render(request, 'website/cart.html', {'cart': {}, 'total': 0, 'total_quantity': 0})

    cleaned_cart, total, products_by_id = build_cleaned_cart(cart)

    if cleaned_cart != cart:
        save_cart(request, cleaned_cart)
        cart = cleaned_cart

    if not cart:
        return render(request, 'website/cart.html', {'cart': {}, 'total': 0, 'total_quantity': 0})

    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            # Create order
            order = form.save(commit=False)
            order.total_price = total
            order.status = 'pending'
            order.save()

            # Create order items
            for product_id, item in cart.items():
                product = products_by_id.get(int(product_id)) or Product.objects.get(id=int(product_id))
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=item['quantity'],
                    price=Decimal(str(item['price']))
                )

            schedule_order_notifications(order, action='pending_order')

            # Clear cart
            request.session['cart'] = {}
            request.session['order_id'] = order.id

            return redirect('website:order_confirmation')
    else:
        form = OrderForm()

    total_quantity = sum(item['quantity'] for item in cart.values())

    context = {
        'cart': cart,
        'total': total,
        'total_quantity': total_quantity,
        'form': form
    }

    return render(request, 'website/cart.html', context)


def order_confirmation(request):
    """Show order confirmation with tracking code after checkout."""
    order_id = request.session.get('order_id')
    if not order_id:
        return redirect('website:home')

    order = get_object_or_404(Order, id=order_id)

    context = {
        'order': order,
    }

    return render(request, 'website/order_confirmation.html', context)


def order_success(request, tracking_code):
    """Legacy URL — redirect to order tracking."""
    return redirect('website:order_tracking')


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