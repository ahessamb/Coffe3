from django.conf import settings
from django.http import HttpResponsePermanentRedirect


class CanonicalDomainRedirectMiddleware:
    """Redirect alternate domains to the canonical zhinadcoffee.ir host."""

    def __init__(self, get_response):
        self.get_response = get_response
        self.alternate_hosts = {host.lower() for host in settings.CANONICAL_REDIRECT_HOSTS}

    def __call__(self, request):
        host = request.get_host().split(":")[0].lower()
        if host in self.alternate_hosts:
            target = f"{settings.CANONICAL_SITE_URL.rstrip('/')}{request.get_full_path()}"
            return HttpResponsePermanentRedirect(target)
        return self.get_response(request)
