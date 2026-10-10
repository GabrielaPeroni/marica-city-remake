"""Importa manchetes de um feed RSS (Google News por padrão) como notícias externas."""

import unicodedata
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timedelta
from datetime import timezone as dt_timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus, urlparse

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import News, NewsCategory

DEFAULT_FEED_URL = (
    "https://news.google.com/rss/search?q={query}+when:{days}d"
    "&hl=pt-BR&gl=BR&ceid=BR:pt-419"
)
IMPORTER_USERNAME = "importador-noticias"
MAX_FEED_BYTES = 5 * 1024 * 1024
USER_AGENT = "MaricaCity-NewsImporter/1.0"


@dataclass(frozen=True)
class FeedItem:
    title: str
    source_name: str
    source_url: str
    published_at: datetime


def build_feed_url(query, days):
    template = getattr(settings, "NEWS_FEED_URL", "") or DEFAULT_FEED_URL
    return template.format(query=quote_plus(query), days=days)


def fetch_feed(url, timeout=20):
    if urlparse(url).scheme != "https":
        raise ValueError("O feed de notícias precisa usar https.")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        return response.read(MAX_FEED_BYTES)


def _fold(text):
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(c for c in normalized if not unicodedata.combining(c)).casefold()


def parse_feed(xml_bytes):
    items = []
    for node in ET.fromstring(xml_bytes).iter("item"):
        title = (node.findtext("title") or "").strip()
        link = (node.findtext("link") or "").strip()
        source = (node.findtext("source") or "").strip()
        pub_date = node.findtext("pubDate")
        if not title or not pub_date or urlparse(link).scheme != "https":
            continue
        try:
            published_at = parsedate_to_datetime(pub_date)
        except (TypeError, ValueError):
            continue
        if published_at.tzinfo is None:
            published_at = published_at.replace(tzinfo=dt_timezone.utc)
        # O Google News anexa " - Veículo" ao título.
        if source and title.endswith(f" - {source}"):
            title = title[: -len(source) - 3].strip()
        items.append(FeedItem(title[:200], source[:120], link, published_at))
    return items


def get_importer_user():
    user, created = get_user_model().objects.get_or_create(
        username=IMPORTER_USERNAME, defaults={"is_active": False}
    )
    if created:
        user.set_unusable_password()
        user.save(update_fields=["password"])
    return user


def import_items(items, *, days, limit, keyword="marica", now=None):
    """Grava itens dentro da janela [now - days, now]; ignora duplicados."""
    now = now or timezone.now()
    since = now - timedelta(days=days)
    category, _ = NewsCategory.objects.get_or_create(name=NewsCategory.NEWS)
    author = get_importer_user()
    known = set(
        News.objects.exclude(source_url="").values_list("source_url", flat=True)
    )

    created = 0
    for item in sorted(items, key=lambda i: i.published_at, reverse=True):
        if created >= limit:
            break
        if not since <= item.published_at <= now:
            continue
        if keyword and keyword not in _fold(item.title):
            continue
        if item.source_url in known:
            continue
        source = item.source_name or "veículo externo"
        News.objects.create(
            title=item.title,
            content=f"Matéria publicada por {source}. Leia a íntegra no site original.",
            excerpt=f"Publicado por {source}.",
            category=category,
            status=News.PUBLISHED,
            publish_date=item.published_at,
            author=author,
            source_name=item.source_name,
            source_url=item.source_url,
        )
        known.add(item.source_url)
        created += 1
    return created


def purge_imported():
    deleted, _ = News.objects.exclude(source_url="").delete()
    return deleted
