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
        done = 0
        for model in MODELS:
            for obj in model.objects.all().iterator():
                if done >= options["limit"]:
                    break
                if not needs_translation(obj):
                    continue
                try:
                    translate_object(obj)
                except (URLError, TimeoutError, ConnectionError) as exc:
                    self.stderr.write(f"Ollama indisponível ({exc}); tente mais tarde.")
                    return
                done += 1
                self.stdout.write(f"  {model.__name__} {obj.pk}")
        self.stdout.write(self.style.SUCCESS(f"{done} item(ns) traduzido(s)."))
