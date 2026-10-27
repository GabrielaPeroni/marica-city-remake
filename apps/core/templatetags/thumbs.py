from django import template

from apps.core.thumbnails import thumbnail_url

register = template.Library()


@register.filter
def thumb(field, width):
    """{{ image|thumb:960 }} -> URL of a WebP copy at most 960px wide."""
    return thumbnail_url(field, int(width))


@register.filter
def srcset(field, widths):
    """{{ image|srcset:"480,960" }} -> "url 480w, url 960w"."""
    if not field:
        return ""
    return ", ".join(
        f"{thumbnail_url(field, int(w))} {int(w)}w" for w in str(widths).split(",")
    )
