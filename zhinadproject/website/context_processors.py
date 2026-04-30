from .models import SiteSettings


def site_settings(request):
    settings = SiteSettings.objects.first()
    hero_images = []
    if settings:
        hero_images = list(settings.hero_images.filter(is_active=True).order_by("order", "id"))
    return {
        "site_settings": settings,
        "home_hero_images": hero_images,
    }

