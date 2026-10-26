import logging
import time

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import close_old_connections

logger = logging.getLogger(__name__)

JOBS = ["crawl_events", "fetch_news"]


class Command(BaseCommand):
    help = "Processo de fundo: roda os importadores a cada --interval horas."

    def add_arguments(self, parser):
        parser.add_argument("--interval", type=float, default=6)
        parser.add_argument("--once", action="store_true")

    def handle(self, *args, **options):
        while True:
            for job in JOBS:
                close_old_connections()
                try:
                    call_command(job, stdout=self.stdout)
                except Exception:
                    logger.exception("Job %s falhou", job)
            if options["once"]:
                return
            time.sleep(options["interval"] * 3600)
