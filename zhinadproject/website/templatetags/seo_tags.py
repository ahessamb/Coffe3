import json

from django import template
from django.utils.safestring import mark_safe

from website.seo import build_media_url, truncate_meta

register = template.Library()


@register.filter
def meta_truncate(value, max_length=155):
    return truncate_meta(value, int(max_length))


@register.filter
def absolute_media(value):
    return build_media_url(getattr(value, "url", value))


@register.simple_tag
def json_ld(data):
    return mark_safe(
        f'<script type="application/ld+json">{json.dumps(data, ensure_ascii=False)}</script>'
    )
