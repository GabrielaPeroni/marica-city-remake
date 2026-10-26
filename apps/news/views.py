from django.core.paginator import Paginator
from django.db.models import Case, Count, IntegerField, Q, Value, When
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from .models import News, NewsCategory

PAGE_SIZE = 12


def news_list_view(request):
    """Agenda de eventos de Maricá, seguida de avisos e manchetes"""
    category_filter = request.GET.get("category", "all")
    sort_by = request.GET.get("sort", "newest")

    published = News.objects.published().select_related("category", "author")
    upcoming_events = published.upcoming_events()
    showing_agenda = category_filter in ("all", NewsCategory.EVENT)

    news_items = published
    if category_filter != "all":
        news_items = news_items.filter(category__name=category_filter)
    if showing_agenda:
        news_items = news_items.exclude(pk__in=upcoming_events.values("pk"))

    if sort_by == "oldest":
        news_items = news_items.order_by("publish_date")
    elif sort_by == "popular":
        news_items = news_items.order_by("-view_count", "-publish_date")
    else:  # mais recentes (padrão): conteúdo próprio antes das manchetes externas
        news_items = news_items.annotate(
            is_press=Case(
                When(source_url="", then=Value(0)),
                When(category__name=NewsCategory.EVENT, then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            )
        ).order_by("is_press", "-publish_date")

    categories = NewsCategory.objects.annotate(
        published_count=Count(
            "news_items",
            filter=Q(
                news_items__status=News.PUBLISHED,
                news_items__publish_date__lte=timezone.now(),
            ),
        )
    )

    page = Paginator(news_items, PAGE_SIZE).get_page(request.GET.get("page"))
    agenda = list(upcoming_events) if showing_agenda and page.number == 1 else []

    context = {
        "news_items": page,
        "agenda": agenda,
        "own_items": [item for item in page if not item.is_external],
        "press_items": [item for item in page if item.is_external],
        "active_category": next(
            (c for c in categories if c.name == category_filter), None
        ),
        "total_count": page.paginator.count,
        "categories": categories,
        "current_category": category_filter,
        "current_sort": sort_by,
        "upcoming_events": upcoming_events,
        "upcoming_count": upcoming_events.count(),
        "featured_items": published.filter(is_featured=True)[:3],
    }

    return render(request, "news/news_list.html", context)


def news_detail_view(request, slug):
    """Exibir página de detalhes de uma única notícia/evento"""
    news_item = get_object_or_404(
        News, slug=slug, status=News.PUBLISHED, publish_date__lte=timezone.now()
    )

    # Incrementar contador de visualizações
    news_item.increment_view_count()

    # Obter notícias relacionadas (mesma categoria, excluir atual)
    related_news = (
        News.objects.filter(
            category=news_item.category,
            status=News.PUBLISHED,
            publish_date__lte=timezone.now(),
        )
        .exclude(id=news_item.id)
        .select_related("category")
        .order_by("-publish_date")[:3]
    )

    context = {
        "news_item": news_item,
        "related_news": related_news,
    }

    return render(request, "news/news_detail.html", context)
