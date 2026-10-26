"""Tradução automática do conteúdo (lugares, eventos, avaliações) via Ollama.

Cada modelo traduzível guarda as versões em ``translations``:
``{"en": {"name": "..."}, "es": {...}, "source": "<hash dos campos em pt>"}``.
Quando o texto em português muda, o hash deixa de bater e o item volta a
ser traduzido na próxima execução de ``translate_content``.
"""

import hashlib
import json
import logging
import urllib.request

from django.conf import settings
from django.utils.translation import get_language

logger = logging.getLogger(__name__)

TARGETS = {"en": "English", "es": "Spanish (Latin America)"}


def source_hash(obj):
    text = "\x1f".join(getattr(obj, f) or "" for f in obj.TRANSLATABLE_FIELDS)
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def needs_translation(obj):
    data = obj.translations or {}
    return data.get("source") != source_hash(obj) or any(t not in data for t in TARGETS)


def translated(obj, field):
    """Campo no idioma ativo, ou o original em português."""
    lang = (get_language() or "")[:2]
    value = ((obj.translations or {}).get(lang) or {}).get(field)
    return value or getattr(obj, field)


def is_machine_translated(obj):
    lang = (get_language() or "")[:2]
    return lang in TARGETS and bool((obj.translations or {}).get(lang))


def _ollama(prompt):
    body = json.dumps(
        {
            "model": settings.OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.1},
        }
    ).encode()
    request = urllib.request.Request(
        f"{settings.OLLAMA_URL}/api/generate",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=300) as response:  # noqa: S310
        return json.loads(json.loads(response.read())["response"])


def translate_object(obj, ask=None):
    ask = ask or _ollama
    fields = {f: getattr(obj, f) for f in obj.TRANSLATABLE_FIELDS if getattr(obj, f)}
    data = {"source": source_hash(obj)}
    for lang, language in TARGETS.items():
        prompt = (
            f"Translate the values of this JSON object from Brazilian Portuguese "
            f"into {language}. It is content from a tourism guide about Maricá, "
            f"Rio de Janeiro. Every value must be written in {language}. Only proper "
            "names of specific places, venues, streets or events (for example "
            "'Lagoa de Araçatiba', 'Cine Henfil', 'FLIM') stay as they are; ordinary "
            "words such as 'hotéis', 'praia' or 'restaurantes' must be translated. "
            "Keep line breaks and do not add anything. Reply with a JSON object "
            "with exactly the same keys.\n\n" + json.dumps(fields, ensure_ascii=False)
        )
        result = ask(prompt)
        data[lang] = {
            k: str(result.get(k, "")).strip() for k in fields if result.get(k)
        }
    obj.translations = data
    type(obj).objects.filter(pk=obj.pk).update(translations=data)
    return data
