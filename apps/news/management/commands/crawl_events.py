from django.core.management.base import BaseCommand, CommandError

from apps.news import event_crawler


class Command(BaseCommand):
    help = "Busca eventos anunciados no portal da Prefeitura e os envia para triagem."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=21)
        parser.add_argument("--file", help="Lê a resposta da API de um arquivo")

    def handle(self, *args, **options):
        try:
            if options["file"]:
                with open(options["file"], "rb") as fh:
                    posts = event_crawler.parse_prefeitura_posts(fh.read())
            else:
                posts = event_crawler.fetch_prefeitura_posts(days=options["days"])
        except Exception as exc:
            raise CommandError(f"Não foi possível ler a Prefeitura: {exc}") from exc

        created = event_crawler.store_candidates(posts)
        self.stdout.write(
            self.style.SUCCESS(
                f"{created} evento(s) novo(s) para triagem de {len(posts)} post(s)."
            )
        )
