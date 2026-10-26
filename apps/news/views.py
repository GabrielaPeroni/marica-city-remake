from django.core.paginator import Paginator
from django.db.models import Case, IntegerField, Q, Value, When
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from .models import News

PAGE_SIZE = 12


def news_list_view(request):
    """Agenda de eventos de Maricá: próximos e anteriores"""
    events = News.objects.published().events().select_related("category", "author")
    upcoming_events = events.upcoming_events()
    past_events = events.exclude(pk__in=upcoming_events.values("pk")).order_by(
        "-event_date", "-publish_date"
    )

    page = Paginator(past_events, PAGE_SIZE).get_page(request.GET.get("page"))

    context = {
        "news_items": page,
        "agenda": list(upcoming_events) if page.number == 1 else [],
        "upcoming_events": upcoming_events,
        "upcoming_count": upcoming_events.count(),
    }
    return render(request, "news/news_list.html", context)


def news_detail_view(request, slug):
    """Exibir a página de um evento; conteúdo que não é evento não é público"""
    event = get_object_or_404(News.objects.published().events(), slug=slug)
    event.increment_view_count()

    now = timezone.now()
    related_events = (
        News.objects.published()
        .events()
        .exclude(id=event.id)
        .select_related("category")
        .annotate(
            is_past=Case(
                When(Q(event_date__gt=now) | Q(event_end_date__gt=now), then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            )
        )
        .order_by("is_past", "event_date", "-publish_date")[:3]
    )

    return render(
        request,
        "news/news_detail.html",
        {"news_item": event, "related_news": related_events},
    )
