from django.utils.http import url_has_allowed_host_and_scheme


def is_speculative(request):
    """True for prefetch/prerender requests, which the visitor may never see."""
    return "prefetch" in request.headers.get("Sec-Purpose", "")


def safe_next(request, default):
    """Return the POSTed `next` URL when it is local, otherwise `default`."""
    target = request.POST.get("next", "")
    if target and url_has_allowed_host_and_scheme(
        target, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return target
    return default
