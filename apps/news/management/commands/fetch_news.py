from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.news import importer


class Command(BaseCommand):
    help = "Importa manchetes recentes sobre Maricá (até hoje) como notícias externas."

    def add_arguments(self, parser):
        parser.add_argument("--query", default="Maricá")
        parser.add_argument("--days", type=int, default=30)
        parser.add_argument("--limit", type=int, default=40)
        parser.add_argument("--file", help="Lê o feed de um arquivo em vez da rede")
        parser.add_argument(
            "--purge",
            action="store_true",
            help="Remove todas as notícias importadas e sai",
        )

    def handle(self, *args, **options):
        if options["purge"]:
            deleted = importer.purge_imported()
            self.stdout.write(self.style.SUCCESS(f"{deleted} registro(s) removido(s)."))
            return

        try:
            if options["file"]:
                xml_bytes = Path(options["file"]).read_bytes()
            else:
                url = importer.build_feed_url(options["query"], options["days"])
                xml_bytes = importer.fetch_feed(url)
            items = importer.parse_feed(xml_bytes)
        except Exception as exc:
            raise CommandError(f"Não foi possível ler o feed: {exc}") from exc

        created = importer.import_items(
            items, days=options["days"], limit=options["limit"]
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"{created} notícia(s) importada(s) de {len(items)} item(ns) no feed."
            )
        )
