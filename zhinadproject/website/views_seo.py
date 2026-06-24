from django.http import HttpResponse

from website.seo import get_canonical_site_url


def robots_txt(request):
    site_url = get_canonical_site_url()
    lines = [
        "User-agent: *",
        "Allow: /",
        "Disallow: /cart/",
        "Disallow: /order/",
        "Disallow: /admin/",
        "Disallow: /cms/",
        "Disallow: /_nested_admin/",
        "",
        f"Sitemap: {site_url}/sitemap.xml",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")
