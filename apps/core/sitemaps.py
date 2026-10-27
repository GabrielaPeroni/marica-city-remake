from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from apps.explore.models import Place
from apps.news.models import News


class PagesSitemap(Sitemap):
    def items(self):
        return ["core:landing", "explore:explore", "news:news_list", "core:about"]

    def location(self, item):
        return reverse(item)


class PlacesSitemap(Sitemap):
    def items(self):
        return Place.objects.public().order_by("pk")

    def location(self, place):
        return reverse("explore:place_detail", args=[place.pk])

    def lastmod(self, place):
        return place.updated_at


class EventsSitemap(Sitemap):
    def items(self):
        return News.objects.published().events().order_by("pk")

    def location(self, event):
        return reverse("news:news_detail", args=[event.slug])

    def lastmod(self, event):
        return event.updated_at


SITEMAPS = {"pages": PagesSitemap, "places": PlacesSitemap, "events": EventsSitemap}
