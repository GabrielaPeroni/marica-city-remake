from urllib.parse import urlparse

from django import template
from django.utils.http import url_has_allowed_host_and_scheme

register = template.Library()


@register.simple_tag(takes_context=True)
def back_url(context, default):
    """Página de onde a pessoa veio (next enviado, ?next= ou Referer), ou `default`.

    Ignora links externos e a própria página (ex.: o formulário recarregado com erros).
    """
    request = context["request"]
    for candidate in (
        request.POST.get("next"),
        request.GET.get("next"),
        request.META.get("HTTP_REFERER"),
    ):
        if not candidate or not url_has_allowed_host_and_scheme(
            candidate,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            continue
        parsed = urlparse(candidate)
        if parsed.path == request.path:
            continue
        return parsed.path + (f"?{parsed.query}" if parsed.query else "")
    return default
