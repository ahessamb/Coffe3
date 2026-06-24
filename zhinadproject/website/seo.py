"""SEO helpers: canonical URLs and domain redirects."""

from django.conf import settings
from django.urls import reverse


def get_canonical_site_url() -> str:
    return settings.CANONICAL_SITE_URL.rstrip("/")


def build_canonical_url(path: str) -> str:
    if not path.startswith("/"):
        path = f"/{path}"
    return f"{get_canonical_site_url()}{path}"


def build_media_url(relative_url: str) -> str:
    if not relative_url:
        return ""
    if relative_url.startswith(("http://", "https://")):
        return relative_url
    if not relative_url.startswith("/"):
        relative_url = f"/{relative_url}"
    return f"{get_canonical_site_url()}{relative_url}"


def truncate_meta(text: str, max_length: int = 155) -> str:
    text = " ".join(str(text or "").split())
    if len(text) <= max_length:
        return text
    trimmed = text[: max_length - 1]
    if " " in trimmed:
        trimmed = trimmed.rsplit(" ", 1)[0]
    return f"{trimmed}…"


def product_json_ld(product) -> dict:
    data = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": product.title,
        "description": truncate_meta(product.description, 300),
        "url": build_canonical_url(
            reverse("website:product_detail", kwargs={"slug": product.slug})
        ),
    }
    if product.main_image:
        data["image"] = build_media_url(product.main_image.url)
    if product.price is not None:
        availability = (
            "https://schema.org/InStock"
            if product.is_buyable
            else "https://schema.org/OutOfStock"
        )
        data["offers"] = {
            "@type": "Offer",
            "priceCurrency": "IRR",
            "price": str(int(product.price)),
            "availability": availability,
            "url": data["url"],
        }
    return data


def article_json_ld(page) -> dict:
    data = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": page.title,
        "description": truncate_meta(page.excerpt or page.title, 300),
        "datePublished": page.published_at.isoformat(),
        "dateModified": page.updated_at.isoformat(),
        "url": build_canonical_url(
            reverse("website:blog_detail", kwargs={"slug": page.slug})
        ),
        "author": {
            "@type": "Organization",
            "name": page.author or "ژیناد",
        },
        "publisher": {
            "@type": "Organization",
            "name": "ژیناد",
            "url": get_canonical_site_url(),
        },
    }
    if page.featured_image:
        data["image"] = build_media_url(page.featured_image.url)
    return data
