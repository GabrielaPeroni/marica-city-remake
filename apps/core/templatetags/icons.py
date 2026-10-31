import logging
from functools import lru_cache
from pathlib import Path

from django import template
from django.conf import settings
from django.utils.html import format_html_join
from django.utils.safestring import mark_safe

register = template.Library()
logger = logging.getLogger(__name__)

ICONS_DIR = Path(__file__).resolve().parent.parent / "icons"


@lru_cache(maxsize=None)
def _svg_body(name):
    """O SVG copiado pelo build:css, sem a tag de abertura: (atributos, conteúdo)."""
    svg = (ICONS_DIR / f"{name}.svg").read_text(encoding="utf-8").strip()
    head, _, rest = svg.partition(">")
    return head.removeprefix("<svg").strip(), rest


@register.simple_tag
def icon(name, **attrs):
    """{% icon "map-pin" class="size-4" %} -> <svg> Lucide inline (currentColor).

    Decorativo (aria-hidden) por padrão; com aria_label vira role="img". Underscores nos
    nomes viram hífens (data_foo -> data-foo).
    """
    try:
        svg_attrs, body = _svg_body(name)
    except FileNotFoundError:
        if settings.DEBUG or getattr(settings, "ICONS_STRICT", False):
            raise template.TemplateSyntaxError(
                f'Icon "{name}" not found in apps/core/icons/; run npm run build:css.'
            )
        logger.warning("Missing icon %s", name)
        return ""

    extra = {key.replace("_", "-"): value for key, value in attrs.items()}
    if "aria-label" in extra:
        extra.setdefault("role", "img")
    else:
        extra.setdefault("aria-hidden", "true")
    extra.setdefault("focusable", "false")
    extra["class"] = f"lucide lucide-{name} {extra.get('class', '')}".strip()

    rendered = format_html_join(" ", '{}="{}"', extra.items())
    return mark_safe(f"<svg {svg_attrs} {rendered}>{body}")
