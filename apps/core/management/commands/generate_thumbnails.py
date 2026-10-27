from django.core.management.base import BaseCommand

from apps.core.thumbnails import generate_all
from apps.explore.models import PlaceImage
from apps.news.models import News


class Command(BaseCommand):
    help = "Gera as cópias WebP redimensionadas das imagens enviadas (thumbs/)."

    def handle(self, *args, **options):
        fields = [p.image for p in PlaceImage.objects.all()]
        fields += [n.featured_image for n in News.objects.exclude(featured_image="")]
        for field in fields:
            generate_all(field)
        self.stdout.write(
            self.style.SUCCESS(f"{len(fields)} imagem(ns) processada(s).")
        )
