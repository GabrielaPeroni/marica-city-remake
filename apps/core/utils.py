from django.utils.http import url_has_allowed_host_and_scheme


def is_speculative(request):
    """True for prefetch/prerender requests, which the visitor may never see."""
    return "prefetch" in request.headers.get("Sec-Purpose", "")


def is_local_url(request, url):
    """True for a URL on this site (blocks open redirects through ?next= or Referer)."""
    return bool(url) and url_has_allowed_host_and_scheme(
        url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    )


def safe_next(request, default):
    """Return the POSTed `next` URL when it is local, otherwise `default`."""
    target = request.POST.get("next", "")
    return target if is_local_url(request, target) else default
