from contextlib import closing
from itertools import islice
from urllib.error import URLError

from django.core.management.base import BaseCommand

from apps.core.content_translation import needs_translation, translate_object
from apps.explore.models import Category, Place, PlaceReview
from apps.news.models import News

MODELS = [Category, Place, PlaceReview, News]


class Command(BaseCommand):
    help = "Traduz para inglês e espanhol o conteúdo novo ou alterado (via Ollama)."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=200)

    def handle(self, *args, **options):
        pending = (
            obj
            for model in MODELS
            for obj in model.objects.iterator()
            if needs_translation(obj)
        )
        # closing(): if we stop early, the Postgres server-side cursor behind
        # .iterator() is closed now, not later inside someone else's transaction
        with closing(pending):
            done = 0
            for obj in islice(pending, options["limit"]):
                try:
                    translate_object(obj)
                except (URLError, TimeoutError, ConnectionError) as exc:
                    self.stderr.write(f"Ollama indisponível ({exc}); tente mais tarde.")
                    return
                done += 1
                self.stdout.write(f"  {type(obj).__name__} {obj.pk}")
        self.stdout.write(self.style.SUCCESS(f"{done} item(ns) traduzido(s)."))
