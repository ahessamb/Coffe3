from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .models import ContentPage, Product


class StaticViewSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return ["home", "products", "about", "contact", "location", "magazine"]

    def location(self, item):
        return reverse(f"website:{item}")


class ProductSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.9

    def items(self):
        return Product.objects.filter(is_active=True)

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return reverse("website:product_detail", kwargs={"slug": obj.slug})


class BlogSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.7

    def items(self):
        return ContentPage.objects.filter(page_type="blog_post", is_published=True)

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return reverse("website:blog_detail", kwargs={"slug": obj.slug})
