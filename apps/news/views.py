from datetime import timedelta

from django.core.paginator import Paginator
from django.db.models import Case, Count, IntegerField, Q, Value, When
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from .models import News, NewsCategory

PAGE_SIZE = 13  # 1 destaque + 12 no grid
LEAD_MAX_AGE_DAYS = 14


def news_list_view(request):
    """Exibir lista de todas as notícias e eventos publicados"""
    # Obter parâmetros de filtro
    category_filter = request.GET.get("category", "all")
    sort_by = request.GET.get("sort", "newest")

    # Consulta base - apenas itens publicados com publish_date <= agora
    news_items = News.objects.filter(
        status=News.PUBLISHED, publish_date__lte=timezone.now()
    ).select_related("category", "author")

    # Filtrar por categoria se especificado
    if category_filter != "all":
        news_items = news_items.filter(category__name=category_filter)

    # Ordenar
    if sort_by == "oldest":
        news_items = news_items.order_by("publish_date")
    elif sort_by == "popular":
        news_items = news_items.order_by("-view_count", "-publish_date")
    else:  # mais recentes (padrão): conteúdo próprio antes das manchetes externas
        news_items = news_items.annotate(
            is_press=Case(
                When(source_url="", then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            )
        ).order_by("is_press", "-publish_date")

    # Obter categorias para menu de filtro
    categories = NewsCategory.objects.annotate(
        published_count=Count(
            "news_items",
            filter=Q(
                news_items__status=News.PUBLISHED,
                news_items__publish_date__lte=timezone.now(),
            ),
        )
    )

    # Separar eventos futuros
    upcoming_events = news_items.filter(
        category__name=NewsCategory.EVENT, event_date__gt=timezone.now()
    ).order_by("event_date")[:3]

    # Obter itens em destaque
    featured_items = news_items.filter(is_featured=True)[:3]

    page = Paginator(news_items, PAGE_SIZE).get_page(request.GET.get("page"))
    # Só um destaque recente ocupa o topo; um antigo não deve ficar preso ali.
    lead_item = None
    if page.number == 1 and sort_by == "newest" and category_filter == "all":
        recent = timezone.now() - timedelta(days=LEAD_MAX_AGE_DAYS)
        lead_item = news_items.filter(
            is_featured=True, publish_date__gte=recent, source_url=""
        ).first()

    listed = [item for item in page if item != lead_item]
    own_items = [item for item in listed if not item.is_external]
    press_items = [item for item in listed if item.is_external]

    active_category = next((c for c in categories if c.name == category_filter), None)

    context = {
        "news_items": page,
        "lead_item": lead_item,
        "own_items": own_items,
        "press_items": press_items,
        "active_category": active_category,
        "total_count": page.paginator.count,
        "categories": categories,
        "current_category": category_filter,
        "current_sort": sort_by,
        "upcoming_events": upcoming_events,
        "featured_items": featured_items,
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
