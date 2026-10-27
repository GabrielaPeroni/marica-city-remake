from django.core.management.base import BaseCommand

from apps.core import demo_snapshot
from apps.explore.models import Place


class Command(BaseCommand):
    help = "Cria o conteúdo de demonstração (snapshot) num banco que ainda não tem lugares."

    def handle(self, *args, **options):
        if Place.objects.exists():
            self.stdout.write("Já há lugares no banco; nada a carregar.")
            return
        created = demo_snapshot.load()
        self.stdout.write(
            self.style.SUCCESS(f"{created} lugares de demonstração criados.")
        )
