from .models import SiteSettings
from .seo import build_canonical_url, build_media_url, get_canonical_site_url


def _organization_json_ld(settings_obj, site_url):
    if not settings_obj:
        return None

    data = {
        "@context": "https://schema.org",
        "@type": ["Organization", "LocalBusiness"],
        "name": "ژیناد",
        "alternateName": "Zhinad Coffee",
        "url": site_url,
        "description": "قهوه و شکلات دست‌ساز با کیفیت ممتاز در مشهد",
        "image": build_media_url(settings_obj.logo_image.url)
        if settings_obj.logo_image and settings_obj.logo_image.name
        else f"{site_url}/static/website/images/logo.png",
    }

    if settings_obj.contact_phone:
        data["telephone"] = settings_obj.contact_phone
    if settings_obj.contact_email:
        data["email"] = settings_obj.contact_email
    if settings_obj.address:
        address = {
            "@type": "PostalAddress",
            "streetAddress": settings_obj.address,
            "addressLocality": "مشهد",
            "addressCountry": "IR",
        }
        data["address"] = address
    if settings_obj.address_lat is not None and settings_obj.address_lng is not None:
        data["geo"] = {
            "@type": "GeoCoordinates",
            "latitude": float(settings_obj.address_lat),
            "longitude": float(settings_obj.address_lng),
        }

    return data


def site_settings(request):
    settings_obj = SiteSettings.objects.first()
    hero_images = []
    if settings_obj:
        hero_images = list(settings_obj.hero_images.filter(is_active=True).order_by("order", "id"))

    site_url = get_canonical_site_url()
    canonical_url = build_canonical_url(request.path)

    return {
        "site_settings": settings_obj,
        "home_hero_images": hero_images,
        "canonical_site_url": site_url,
        "canonical_url": canonical_url,
        "organization_json_ld": _organization_json_ld(settings_obj, site_url),
        "default_og_image": f"{site_url}/static/website/images/logo.png",
    }

