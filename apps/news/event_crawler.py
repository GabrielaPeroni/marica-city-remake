"""Encontra eventos anunciados no portal da Prefeitura e os coloca em triagem."""

import html
import json
import re
import unicodedata
import urllib.request
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from datetime import timezone as dt_timezone
from difflib import SequenceMatcher
from urllib.parse import urlencode, urlparse

from django.core.files.base import ContentFile
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .models import EventCandidate, News, NewsCategory

PREFEITURA_API = "https://www.marica.rj.gov.br/wp-json/wp/v2/posts"
# Cultura, Turismo, Esportes, Cultura e Utopias, MARÉ (Companhia de Cultura e Turismo)
PREFEITURA_CATEGORIES = "3329,3345,3326,8185,9175"
MAX_IMAGE_BYTES = 8 * 1024 * 1024
MAX_FEED_BYTES = 5 * 1024 * 1024
USER_AGENT = "MaricaCity-EventCrawler/1.0"
SUMMARY_MAX = 700

MONTHS = {
    "janeiro": 1,
    "fevereiro": 2,
    "marco": 3,
    "abril": 4,
    "maio": 5,
    "junho": 6,
    "julho": 7,
    "agosto": 8,
    "setembro": 9,
    "outubro": 10,
    "novembro": 11,
    "dezembro": 12,
}
_M = "(" + "|".join(MONTHS) + ")"
_D = r"(\d{1,2})(?:º|o)?"

PAST_VERBS = (
    "realizou",
    "reuniu",
    "encerrou",
    "celebrou",
    "recebeu",
    "levou",
    "promoveu",
    "marcou",
    "foi realizad",
    "aconteceu",
)
FUTURE_VERBS = (
    "promove",
    "realiza",
    "tera ",
    "recebe",
    "acontece",
    "sera ",
    "vai ",
    "leva",
    "prepara",
    "divulga",
    "abre",
    "convida",
)
EVENT_WORDS = (
    "festival",
    "show",
    "feira",
    "festa",
    "seminario",
    "mostra",
    "exposicao",
    "campeonato",
    "corrida",
    "pedalada",
    "bike night",
    "encontro",
    "oficina",
    "apresentac",
    "programacao",
    "jogos",
    "torneio",
    "espetaculo",
    "concerto",
    "circuito",
    "portas abertas",
    "natal",
    "carnaval",
    "flim",
)
VENUE_WORDS = (
    "praca",
    "parque",
    "orla",
    "cine",
    "arena",
    "teatro",
    "centro de",
    "lona",
    "casa de",
    "biblioteca",
    "estadio",
    "ginasio",
    "espaco",
    "sitio",
    "deck",
    "lagoa",
    "praia",
    "igreja",
    "concha",
    "complexo",
    "museu",
    "calcadao",
    "boulevard",
    "aldeia",
    "mercado",
)


@dataclass
class Post:
    source_id: str
    url: str
    title: str
    text: str
    published_at: datetime
    image_url: str = ""


@dataclass
class Extraction:
    start: datetime | None = None
    end: datetime | None = None
    location: str = ""
    summary: str = ""
    score: int = 0
    signals: list = field(default_factory=list)


def _strip_html(raw):
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", raw, flags=re.S)
    text = re.sub(r"</p>|<br\s*/?>", "\n", text)
    text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    lines = [re.sub(r"[ \t\xa0]+", " ", line).strip() for line in text.split("\n")]
    return "\n".join(line for line in lines if line)


def parse_prefeitura_posts(payload):
    posts = []
    for item in json.loads(payload):
        published = parse_datetime(item.get("date_gmt") or "")
        link = item.get("link", "")
        if not published or urlparse(link).scheme != "https":
            continue
        media = (item.get("_embedded") or {}).get("wp:featuredmedia") or [{}]
        image = media[0].get("source_url", "") if isinstance(media[0], dict) else ""
        posts.append(
            Post(
                source_id=str(item["id"]),
                url=link,
                title=html.unescape(item["title"]["rendered"]).strip()[:200],
                text=_strip_html(item["content"]["rendered"]),
                published_at=published.replace(tzinfo=dt_timezone.utc),
                image_url=image if urlparse(image).scheme == "https" else "",
            )
        )
    return posts


def fetch_prefeitura_posts(days=21, per_page=50):
    since = (timezone.now() - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%S")
    query = urlencode(
        {
            "categories": PREFEITURA_CATEGORIES,
            "after": since,
            "per_page": per_page,
            "_embed": "wp:featuredmedia",
        }
    )
    return parse_prefeitura_posts(fetch_json(f"{PREFEITURA_API}?{query}"))


def _year_for(month, day, reference):
    """Datas sem ano: assume a próxima ocorrência a partir da publicação."""
    year = reference.year
    try:
        candidate = date(year, month, day)
    except ValueError:
        return None
    if candidate < reference - timedelta(days=60):
        year += 1
    return year


def _make(day, month, year, reference, hour=None, minute=0):
    year = year or _year_for(month, day, reference)
    if year is None:
        return None
    try:
        when = date(int(year), month, day)
    except ValueError:
        return None
    clock = time(hour, minute) if hour is not None else time(0, 0)
    return timezone.make_aware(datetime.combine(when, clock))


def extract_dates(text, reference):
    """Retorna (início, fim) do primeiro intervalo ou data encontrada."""
    folded = _fold(text)
    patterns = [
        # de 30 de outubro a 8 de novembro / entre 30 de outubro e 8 de novembro
        (
            rf"(?:de|entre|dias) {_D} de {_M}(?: de (\d{{4}}))? (?:a|ate|e) {_D} de {_M}"
            rf"(?: de (\d{{4}}))?",
            lambda m: (
                (int(m[1]), MONTHS[m[2]], m[3]),
                (int(m[4]), MONTHS[m[5]], m[6]),
            ),
        ),
        # de 13 a 15 de novembro / nos dias 26 e 27 de outubro / dias 13, 14 e 15 de
        (
            rf"(?:de|dias|entre) {_D}(?:, \d{{1,2}})* (?:a|ate|e) {_D} de {_M}"
            rf"(?: de (\d{{4}}))?",
            lambda m: (
                (int(m[1]), MONTHS[m[3]], m[4]),
                (int(m[2]), MONTHS[m[3]], m[4]),
            ),
        ),
        # 7 de novembro
        (
            rf"\b{_D} de {_M}(?: de (\d{{4}}))?",
            lambda m: ((int(m[1]), MONTHS[m[2]], m[3]), None),
        ),
        # 27/10 or (18/10)
        (
            r"\b(\d{1,2})/(\d{1,2})(?:/(\d{4}))?\b",
            lambda m: ((int(m[1]), int(m[2]), m[3]), None),
        ),
    ]
    for pattern, build in patterns:
        match = re.search(pattern, folded)
        if not match:
            continue
        start_parts, end_parts = build(match)
        if not 1 <= start_parts[1] <= 12:
            continue
        hour, minute = extract_time(folded)
        start = _make(*start_parts, reference, hour, minute)
        end = _make(*end_parts, reference, 23, 59) if end_parts else None
        if start and end and end <= start:
            end = None
        if start:
            return start, end
    return None, None


def extract_time(folded):
    match = re.search(r"(?:as|das|a partir das) (\d{1,2})h(\d{2})?", folded)
    if not match or int(match[1]) > 23:
        return None, 0
    return int(match[1]), int(match[2] or 0)


_CAP = r"[A-ZÁÉÍÓÚÂÊÔÃÕÇ][\wÀ-ÿ’'\-]*"
_LINK = r"(?:de|da|do|das|dos|e|d’|d')"
_PLACE = rf"{_CAP}(?:\s+(?:{_CAP}|{_LINK}))*(?:\s+\([A-Z]+\))?"


def extract_location(text):
    for match in re.finditer(rf"\b(?:no|na|nos|nas|em)\s+({_PLACE})", text):
        place = re.sub(rf"\s+{_LINK}$", "", match[1]).strip()
        folded = _fold(place)
        if not any(word in folded for word in VENUE_WORDS):
            continue
        tail = re.match(rf",\s+(?:no|na|em)\s+({_PLACE})", text[match.end() :])
        if tail and _fold(tail[1]) not in ("marica", "municipio"):
            place = f"{place}, {tail[1]}"
        return place[:200]
    return ""


def _lead(text):
    paragraphs = text.split("\n")
    summary = ""
    for paragraph in paragraphs:
        if len(summary) + len(paragraph) > SUMMARY_MAX and summary:
            break
        summary = f"{summary}\n\n{paragraph}".strip()
    return summary[:SUMMARY_MAX]


def extract(post):
    """Lê um post e devolve o que conseguiu identificar como evento."""
    lead = " ".join(post.text.split("\n")[:2])
    folded_lead = _fold(lead)
    folded_title = _fold(post.title)
    result = Extraction(summary=_lead(post.text))

    result.start, result.end = extract_dates(lead, post.published_at.date())
    if result.start:
        result.score += 40
        result.signals.append("data")
    result.location = extract_location(lead) or extract_location(post.text[:1500])
    if result.location:
        result.score += 20
        result.signals.append("local")
    if any(word in folded_title or word in folded_lead for word in EVENT_WORDS):
        result.score += 20
        result.signals.append("palavra de evento")
    if any(verb in folded_lead for verb in FUTURE_VERBS):
        result.score += 20
        result.signals.append("anúncio")
    if result.start and result.start.date() < post.published_at.date():
        result.score = max(0, result.score - 40)
        result.signals.append("data anterior à publicação")
    if any(verb in folded_lead[:250] for verb in PAST_VERBS):
        result.score = max(0, result.score - 40)
        result.signals.append("cobertura de evento passado")
    return result


def _similar(a, b):
    return SequenceMatcher(None, _fold(a), _fold(b)).ratio()


def find_duplicate(title, start):
    """Evento já publicado com título parecido perto da mesma data."""
    events = News.objects.filter(category__name=NewsCategory.EVENT)
    if start:
        events = events.filter(
            event_date__date__range=(
                start.date() - timedelta(days=3),
                start.date() + timedelta(days=3),
            )
        )
    best = max(events, key=lambda n: _similar(n.title, title), default=None)
    return best if best and _similar(best.title, title) >= 0.55 else None


def same_event(a, b):
    """Dois candidatos no mesmo dia e local provavelmente tratam do mesmo evento."""
    if not a.event_date or not b.event_date:
        return False
    same_day = timezone.localdate(a.event_date) == timezone.localdate(b.event_date)
    return same_day and _fold(a.event_location) == _fold(b.event_location)


def store_candidates(
    posts, source="prefeitura", source_name="Prefeitura de Maricá", now=None
):
    """Cria candidatos para posts que anunciam eventos futuros. Retorna quantos."""
    now = now or timezone.now()
    known = set(
        EventCandidate.objects.filter(source=source).values_list("source_id", flat=True)
    )
    created = 0
    for post in posts:
        if post.source_id in known:
            continue
        found = extract(post)
        if not found.start or (found.end or found.start) < now - timedelta(hours=12):
            continue
        if "cobertura de evento passado" in found.signals and found.score < 40:
            continue
        EventCandidate.objects.create(
            source=source,
            source_id=post.source_id,
            source_name=source_name,
            source_url=post.url,
            source_published_at=post.published_at,
            title=post.title,
            summary=found.summary,
            image_url=post.image_url,
            event_date=found.start,
            event_end_date=found.end,
            event_location=found.location,
            score=min(found.score, 100),
            signals=found.signals,
            possible_duplicate=find_duplicate(post.title, found.start),
        )
        created += 1
    return created


def _fold(text):
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(c for c in normalized if not unicodedata.combining(c)).casefold()


def fetch_json(url, timeout=20):
    if urlparse(url).scheme != "https":
        raise ValueError("A consulta de eventos precisa usar https.")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        return response.read(MAX_FEED_BYTES)


def fetch_image(url):
    if urlparse(url).scheme != "https":
        return None
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=20) as response:  # noqa: S310
        if not response.headers.get_content_type().startswith("image/"):
            return None
        data = response.read(MAX_IMAGE_BYTES + 1)
    return data if len(data) <= MAX_IMAGE_BYTES else None


def approve(candidate, user, image_fetcher=fetch_image):
    """Converte o candidato em um evento publicado."""
    category, _ = NewsCategory.objects.get_or_create(name=NewsCategory.EVENT)
    excerpt = candidate.summary.split("\n")[0]
    if len(excerpt) > 300:
        excerpt = excerpt[:297].rsplit(" ", 1)[0] + "..."
    news = News(
        title=candidate.title,
        content=candidate.summary,
        excerpt=excerpt,
        category=category,
        status=News.PUBLISHED,
        author=user,
        event_date=candidate.event_date,
        event_end_date=candidate.event_end_date,
        event_location=candidate.event_location,
        source_name=candidate.source_name,
        source_url=candidate.source_url,
        image_caption=f"Foto: {candidate.source_name}" if candidate.image_url else "",
    )
    if candidate.image_url:
        try:
            data = image_fetcher(candidate.image_url)
        except OSError:
            data = None
        if data:
            name = urlparse(candidate.image_url).path.rsplit("/", 1)[-1][-80:]
            news.featured_image.save(
                name or "evento.jpg", ContentFile(data), save=False
            )
    news.save()
    candidate.news = news
    candidate.status = EventCandidate.APPROVED
    candidate.reviewed_by = user
    candidate.reviewed_at = timezone.now()
    candidate.save()
    return news


def reject(candidate, user):
    candidate.status = EventCandidate.REJECTED
    candidate.reviewed_by = user
    candidate.reviewed_at = timezone.now()
    candidate.save(update_fields=["status", "reviewed_by", "reviewed_at"])


def reject_many(ids, user):
    """Descarta os candidatos pendentes entre `ids`; devolve quantos foram."""
    return EventCandidate.objects.filter(
        pk__in=ids, status=EventCandidate.PENDING
    ).update(
        status=EventCandidate.REJECTED, reviewed_by=user, reviewed_at=timezone.now()
    )
