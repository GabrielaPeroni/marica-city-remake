from django.core.management.base import BaseCommand

from apps.core import demo_snapshot


class Command(BaseCommand):
    help = "Grava o conteúdo de demonstração atual em apps/core/demo_data (snapshot + fotos)."

    def handle(self, *args, **options):
        data = demo_snapshot.export()
        self.stdout.write(
            self.style.SUCCESS(
                f"{len(data['places'])} lugares, {len(data['events'])} eventos e "
                f"{len(data['users'])} contas de demonstração exportados."
            )
        )
