"""Resized WebP copies of uploaded images, generated once and kept next to the media.

thumbs/<width>/<original path without extension>.webp
"""

import base64
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


def _cached(key, compute, fallback):
    """Valor em cache, ou calcula e guarda; em erro de arquivo, registra e usa o fallback."""
    value = cache.get(key)
    if value:
        return value
    try:
        value = compute()
    except (OSError, ValueError) as exc:
        logger.warning("%s failed: %s", key, exc)
        return fallback
    cache.set(key, value, CACHE_SECONDS)
    return value


def thumbnail_url(field, width):
    """URL of the `width`px WebP copy of an ImageField file; the original on failure."""
    if not field:
        return ""
    name = thumb_name(field.name, width)

    def build():
        if not field.storage.exists(name):
            with field.storage.open(field.name, "rb") as source:
                field.storage.save(name, ContentFile(_render(source, width)))
        return field.storage.url(name)

    return _cached(f"thumb:{name}", build, field.url)


def generate_all(field):
    for width in WIDTHS:
        thumbnail_url(field, width)


def placeholder_uri(field):
    """Prévia de 16 px (data URI) usada como fundo da imagem enquanto ela decodifica."""
    if not field:
        return ""

    def build():
        small = thumb_name(field.name, WIDTHS[0])
        name = small if field.storage.exists(small) else field.name
        with field.storage.open(name, "rb") as source, Image.open(source) as image:
            image = ImageOps.exif_transpose(image).convert("RGB")
            image.thumbnail((16, 16))
            buffer = BytesIO()
            image.save(buffer, "WEBP", quality=40)
        return "data:image/webp;base64," + base64.b64encode(buffer.getvalue()).decode()

    return _cached(f"lqip:{field.name}", build, "")
