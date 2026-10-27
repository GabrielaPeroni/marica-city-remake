import json
import urllib.request
from decimal import Decimal
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from apps.accounts.models import User
from apps.explore.models import Category, Place, PlaceImage

DATA_FILE = Path(__file__).resolve().parents[2] / "demo_data" / "places.json"
MAX_IMAGE_BYTES = 8 * 1024 * 1024
USER_AGENT = "MaricaCityDemo/1.0"


def download_image(url):
    if not url.startswith("https://"):
        raise ValueError("only https image URLs are allowed")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        content_type = response.headers.get("Content-Type", "")
        if not content_type.startswith("image/"):
            raise ValueError(f"unexpected content type: {content_type}")
        data = response.read(MAX_IMAGE_BYTES + 1)
    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError("image is larger than 8 MB")
    return data


class Command(BaseCommand):
    help = "Cria os lugares reais de demonstração (aprovados) a partir de demo_data/places.json"

    def add_arguments(self, parser):
        parser.add_argument(
            "--with-images",
            action="store_true",
            help="Baixa as fotos do Wikimedia Commons (acesso à rede)",
        )

    def handle(self, *args, **options):
        owner = (
            User.objects.filter(is_active=True)
            .filter(Q(is_superuser=True) | Q(is_staff=True))
            .order_by("-is_superuser", "id")
            .first()
        )
        if owner is None:
            raise CommandError("No active superuser or staff user found.")

        entries = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        categories = {c.slug: c for c in Category.objects.all()}
        needed = {slug for entry in entries for slug in entry["categories"]}
        missing = sorted(needed - set(categories))
        if missing:
            raise CommandError(f"Missing categories: {', '.join(missing)}")

        created = 0
        for entry in entries:
            image = entry.get("image")
            place = Place.objects.filter(name=entry["name"]).first()
            if place is not None:
                self.stdout.write(f"Already exists: {place.name}")
                if options["with_images"] and image and not place.images.exists():
                    self._attach_image(place, image)
                continue

            lat, lng = entry.get("latitude"), entry.get("longitude")
            place = Place.objects.create(
                name=entry["name"],
                description=entry["description"],
                address=entry["address"],
                latitude=None if lat is None else Decimal(str(lat)),
                longitude=None if lng is None else Decimal(str(lng)),
                created_by=owner,
                is_approved=True,
                is_active=True,
            )
            place.categories.set([categories[slug] for slug in entry["categories"]])
            created += 1
            self.stdout.write(self.style.SUCCESS(f"Created: {place.name}"))

            if options["with_images"] and image:
                self._attach_image(place, image)

        self.stdout.write(self.style.SUCCESS(f"Done. {created} place(s) created."))

    def _attach_image(self, place, image):
        try:
            data = download_image(image["thumb_url"])
        except Exception as exc:
            self.stderr.write(f"Image skipped for {place.name}: {exc}")
            return
        source = f"{image['author']} / Wikimedia Commons ({image['license']})"
        if image.get("illustrative"):
            credit = f" Imagem ilustrativa ({image['illustrative']}): {source}."
        else:
            credit = f" Foto: {source}."
        extension = Path(image["commons_title"]).suffix.lower() or ".jpg"
        photo = PlaceImage(place=place, caption=place.name, is_primary=True)
        photo.image.save(f"{place.pk}{extension}", ContentFile(data), save=True)
        place.description += credit
        place.save(update_fields=["description"])
