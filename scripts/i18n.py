"""Interface translation catalogs without GNU gettext.

    uv run python scripts/i18n.py extract    # update locale/*/LC_MESSAGES/*.po
    uv run python scripts/i18n.py translate  # draft empty entries with Ollama
    uv run python scripts/i18n.py compile    # write .mo files Django loads

Source strings are Portuguese. Templates go through Django's own
``templatize`` so ``{% translate %}``/``{% blocktranslate %}`` are read exactly
as ``makemessages`` would. Review machine drafts before committing.
"""

import argparse
import io
import json
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

import django  # noqa: E402

django.setup()

from django.utils.translation.template import templatize  # noqa: E402

from babel.messages.catalog import Catalog  # noqa: E402
from babel.messages.extract import extract_javascript, extract_python  # noqa: E402
from babel.messages.mofile import write_mo  # noqa: E402
from babel.messages.pofile import read_po, write_po  # noqa: E402

LANGS = {"en": "English", "es": "Spanish (Latin America)"}
LOCALE = ROOT / "locale"
PY_KEYWORDS = {
    "_": None,
    "_l": None,
    "gettext": None,
    "gettext_lazy": None,
    "ngettext": (1, 2),
    "ngettext_lazy": (1, 2),
    "pgettext": ((1, "c"), 2),
    "pgettext_lazy": ((1, "c"), 2),
    "npgettext": ((1, "c"), 2, 3),
    "npgettext_lazy": ((1, "c"), 2, 3),
}
JS_KEYWORDS = {"gettext": None, "ngettext": (1, 2), "interpolate": None}
SKIP_DIRS = {"migrations", "tests", "__pycache__"}


def _sources():
    for path in sorted((ROOT / "templates").rglob("*")):
        if path.suffix in (".html", ".txt"):
            yield "django", path, "template"
    for path in sorted((ROOT / "apps").rglob("*")):
        if SKIP_DIRS & set(path.parts) or path.name == "tests.py":
            continue
        if path.suffix == ".py":
            yield "django", path, "python"
        elif path.suffix == ".html":
            yield "django", path, "template"
    for path in sorted((ROOT / "static" / "js").rglob("*.js")):
        yield "djangojs", path, "js"


def _messages(path, kind):
    text = path.read_text(encoding="utf-8")
    if kind == "template":
        if "trans" not in text:
            return
        text = templatize(text, origin=str(path))
        # tokenize is strict about indentation; xgettext is not
        text = "\n".join(line.lstrip() for line in text.splitlines())
        fileobj, method, keywords = (
            io.BytesIO(text.encode()),
            extract_python,
            PY_KEYWORDS,
        )
    elif kind == "python":
        fileobj, method, keywords = (
            io.BytesIO(text.encode()),
            extract_python,
            PY_KEYWORDS,
        )
    else:
        fileobj, method, keywords = (
            io.BytesIO(text.encode()),
            extract_javascript,
            JS_KEYWORDS,
        )
    for lineno, funcname, message, comments in method(
        fileobj, keywords, [], {"encoding": "utf-8"}
    ):
        spec = keywords.get(funcname)
        if isinstance(message, tuple):
            context = None
            if isinstance(spec, tuple) and isinstance(spec[0], tuple):
                context, message = message[0], message[1:]
                message = message if len(message) > 1 else message[0]
            if isinstance(message, tuple):
                message = tuple(m for m in message if m) or None
                if message and len(message) == 1:
                    message = message[0]
        else:
            context = None
        if message:
            yield lineno, message, context


def extract():
    templates = {"django": Catalog(), "djangojs": Catalog()}
    for domain, path, kind in _sources():
        rel = path.relative_to(ROOT).as_posix()
        for lineno, message, context in _messages(path, kind):
            templates[domain].add(message, locations=[(rel, lineno)], context=context)
    for lang in LANGS:
        for domain, template in templates.items():
            po_path = LOCALE / lang / "LC_MESSAGES" / f"{domain}.po"
            po_path.parent.mkdir(parents=True, exist_ok=True)
            if po_path.exists():
                with po_path.open("rb") as fh:
                    catalog = read_po(fh, locale=lang)
                catalog.update(template, no_fuzzy_matching=True)
            else:
                catalog = Catalog(locale=lang, project="MaricaCity", domain=domain)
                catalog.update(template, no_fuzzy_matching=True)
            catalog.obsolete.clear()
            with po_path.open("wb") as fh:
                write_po(fh, catalog, width=88, sort_output=False)
            missing = sum(1 for m in catalog if m.id and not _done(m))
            print(f"{lang}/{domain}: {len(catalog)} strings, {missing} untranslated")


def _done(message):
    if isinstance(message.string, tuple):
        return all(message.string)
    return bool(message.string)


def _ollama(prompt, model, url):
    body = json.dumps(
        {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.1},
        }
    ).encode()
    request = urllib.request.Request(
        f"{url}/api/generate", data=body, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(request, timeout=600) as response:  # noqa: S310
        return json.loads(json.loads(response.read())["response"])


def translate(model, url, batch=25):
    for lang, language in LANGS.items():
        for domain in ("django", "djangojs"):
            po_path = LOCALE / lang / "LC_MESSAGES" / f"{domain}.po"
            with po_path.open("rb") as fh:
                catalog = read_po(fh, locale=lang)
            todo = [m for m in catalog if m.id and not _done(m)]
            for start in range(0, len(todo), batch):
                chunk = todo[start : start + batch]
                items = {}
                for i, m in enumerate(chunk):
                    ids = m.id if isinstance(m.id, tuple) else (m.id,)
                    for j, text in enumerate(ids):
                        items[f"{i}.{j}"] = text
                prompt = (
                    f"Translate the interface strings of a tourism website about "
                    f"Maricá, Brazil from Brazilian Portuguese to {language}. Keep "
                    "placeholders like %(name)s, %s, {0} and HTML tags unchanged, "
                    "keep proper nouns (Maricá, MaricaCity, FLIM, street and place "
                    "names) as they are, match capitalisation and punctuation, and "
                    "be concise like UI text. Answer with a JSON object mapping each "
                    "key to its translation.\n\n"
                    + json.dumps(items, ensure_ascii=False)
                )
                result = _ollama(prompt, model, url)
                for i, m in enumerate(chunk):
                    if isinstance(m.id, tuple):
                        m.string = tuple(
                            result.get(f"{i}.{j}", "") for j in range(len(m.id))
                        )
                        if len(m.string) < 2:
                            m.string = (m.string[0], m.string[0])
                    else:
                        m.string = result.get(f"{i}.0", "")
                print(f"{lang}/{domain}: {min(start + batch, len(todo))}/{len(todo)}")
            with po_path.open("wb") as fh:
                write_po(fh, catalog, width=88, sort_output=False)


def compile_():
    for po_path in LOCALE.rglob("*.po"):
        with po_path.open("rb") as fh:
            catalog = read_po(fh)
        with po_path.with_suffix(".mo").open("wb") as fh:
            write_mo(fh, catalog)
        print(f"compiled {po_path.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("extract")
    t = sub.add_parser("translate")
    t.add_argument("--model", default=os.environ.get("OLLAMA_MODEL", "qwen2.5:14b"))
    t.add_argument(
        "--url", default=os.environ.get("OLLAMA_URL", "http://localhost:11434")
    )
    sub.add_parser("compile")
    args = parser.parse_args()
    if args.command == "extract":
        extract()
    elif args.command == "translate":
        translate(args.model, args.url)
    else:
        compile_()
