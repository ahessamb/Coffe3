from django.urls import path
from . import views

app_name = 'website'

urlpatterns = [
    # Static Pages
    path('', views.HomeView.as_view(), name='home'),
    path('about/', views.AboutView.as_view(), name='about'),
    path('contact/', views.ContactView.as_view(), name='contact'),
    path('location/', views.LocationView.as_view(), name='location'),

    # Blog / Magazine
    path('magazine/', views.MagazineView.as_view(), name='magazine'),
    path('magazine/<slug:slug>/', views.BlogDetailView.as_view(), name='blog_detail'),

    # Products
    path('products/', views.ProductListView.as_view(), name='products'),
    path('product/<slug:slug>/', views.ProductDetailView.as_view(), name='product_detail'),

    # Cart
    path('cart/', views.cart_view, name='cart'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/<int:product_id>/', views.update_cart, name='update_cart'),
    path('cart/remove/<int:product_id>/', views.remove_from_cart, name='remove_from_cart'),

    # Order
    path('order/confirmation/', views.order_confirmation, name='order_confirmation'),
    path('order/success/<str:tracking_code>/', views.order_success, name='order_success'),
    path('order/tracking/', views.order_tracking, name='order_tracking'),
]