"""Resized WebP copies of uploaded images, generated once and kept next to the media.

thumbs/<width>/<original path without extension>.webp
"""

import logging
from io import BytesIO
from pathlib import PurePosixPath

from django.core.cache import cache
from django.core.files.base import ContentFile

from PIL import Image, ImageOps

logger = logging.getLogger(__name__)

WIDTHS = (480, 960, 1600)
QUALITY = 78
CACHE_SECONDS = 60 * 60 * 24 * 30


def thumb_name(name, width):
    return str(PurePosixPath("thumbs", str(width), name).with_suffix(".webp"))


def _render(source, width):
    with Image.open(source) as image:
        image = ImageOps.exif_transpose(image)
        if image.mode not in ("RGB", "RGBA"):
            image = image.convert("RGBA" if "transparency" in image.info else "RGB")
        if image.width > width:
            height = round(image.height * width / image.width)
            image = image.resize((width, height), Image.LANCZOS)
        buffer = BytesIO()
        image.save(buffer, "WEBP", quality=QUALITY, method=6)
    return buffer.getvalue()


def thumbnail_url(field, width):
    """URL of the `width`px WebP copy of an ImageField file; the original on failure."""
    if not field:
        return ""
    name = thumb_name(field.name, width)
    key = f"thumb:{name}"
    url = cache.get(key)
    if url:
        return url
    storage = field.storage
    try:
        if not storage.exists(name):
            with storage.open(field.name, "rb") as source:
                storage.save(name, ContentFile(_render(source, width)))
        url = storage.url(name)
    except (OSError, ValueError) as exc:
        logger.warning("thumbnail failed for %s: %s", field.name, exc)
        return field.url
    cache.set(key, url, CACHE_SECONDS)
    return url


def generate_all(field):
    for width in WIDTHS:
        thumbnail_url(field, width)
