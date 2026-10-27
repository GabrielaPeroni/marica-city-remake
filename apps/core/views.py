import logging
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import ngettext
from django.views.decorators.http import require_GET, require_POST

from apps.accounts.models import User
from apps.core.utils import safe_next
from apps.explore.models import Category, Place, PlaceReview
from apps.explore.visits import most_visited
from apps.news import event_crawler
from apps.news.forms import EventCandidateForm, NewsForm
from apps.news.models import EventCandidate, News, NewsCategory

logger = logging.getLogger(__name__)


@require_GET
def health_view(request):
    """Liveness/readiness probe; does a cheap SELECT 1 to also catch DB outages."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    return JsonResponse({"status": "ok"})


def landing_view(request):
    # Lugares em destaque (mais recentes)
    featured_places = (
        Place.objects.filter(is_approved=True, is_active=True)
        .prefetch_related("images", "categories")
        .order_by("-created_at")[:6]
    )

    # Em alta: mais visitados na semana; sem visitas, os cadastrados na semana
    trending_places = list(most_visited())
    if not trending_places:
        day_range = timezone.now() - timedelta(days=7)
        trending_places = (
            Place.objects.filter(
                is_approved=True, is_active=True, created_at__gte=day_range
            )
            .prefetch_related("images", "categories")
            .order_by("-created_at")[:4]
        )

    categories = Category.objects.filter(is_active=True).order_by("display_order")[:8]

    events = News.objects.published().select_related("category")
    upcoming_events = list(events.upcoming_events()[:4])
    # Sem eventos futuros (ex.: site estático), mostra os mais recentes
    recent_events = (
        []
        if upcoming_events
        else list(
            events.filter(category__name=NewsCategory.EVENT)
            .exclude(event_date=None)
            .order_by("-event_date")[:4]
        )
    )

    context = {
        "featured_places": featured_places,
        "trending_places": trending_places,
        "upcoming_events": upcoming_events,
        "recent_events": recent_events,
        "categories": categories,
        "GOOGLE_MAPS_API_KEY": settings.GOOGLE_MAPS_API_KEY,
        "google_client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
    }
    return render(request, "core/landing.html", context)


def about_view(request):
    """View da página sobre"""
    return render(request, "core/about.html")


def calculate_percentage_change(current, previous):
    """Calcular mudança percentual entre dois valores"""
    if previous == 0:
        return 100 if current > 0 else 0
    return round(((current - previous) / previous) * 100, 1)


@login_required
def admin_dashboard_view(request):
    """Dashboard de administração centralizado"""
    if not request.user.can_moderate:
        messages.error(request, _("Você não tem permissão para acessar esta página."))
        return redirect("core:landing")

    # Períodos de tempo
    now = timezone.now()
    week_ago = now - timedelta(days=7)
    two_weeks_ago = now - timedelta(days=14)

    # Obter estatísticas principais
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    total_places = Place.objects.count()
    pending_places = Place.objects.filter(is_approved=False, is_active=True).count()
    approved_places = Place.objects.filter(is_approved=True).count()

    # Estatísticas semanais
    places_this_week = Place.objects.filter(created_at__gte=week_ago).count()
    places_last_week = Place.objects.filter(
        created_at__gte=two_weeks_ago, created_at__lt=week_ago
    ).count()
    places_change = calculate_percentage_change(places_this_week, places_last_week)

    users_this_week = User.objects.filter(date_joined__gte=week_ago).count()
    users_last_week = User.objects.filter(
        date_joined__gte=two_weeks_ago, date_joined__lt=week_ago
    ).count()
    users_change = calculate_percentage_change(users_this_week, users_last_week)

    reviews_this_week = PlaceReview.objects.filter(created_at__gte=week_ago).count()
    reviews_last_week = PlaceReview.objects.filter(
        created_at__gte=two_weeks_ago, created_at__lt=week_ago
    ).count()
    reviews_change = calculate_percentage_change(reviews_this_week, reviews_last_week)

    total_reviews = PlaceReview.objects.count()

    # Estatísticas de notícias
    total_news = News.objects.count()
    published_news = News.objects.filter(status=News.PUBLISHED).count()
    draft_news = News.objects.filter(status=News.DRAFT).count()

    # Usuários recentes (últimos 10)
    recent_users = User.objects.select_related().order_by("-date_joined")[:10]

    context = {
        "total_users": total_users,
        "active_users": active_users,
        "total_places": total_places,
        "pending_places": pending_places,
        "approved_places": approved_places,
        "total_news": total_news,
        "published_news": published_news,
        "draft_news": draft_news,
        # Tendências semanais
        "places_this_week": places_this_week,
        "places_change": places_change,
        "users_this_week": users_this_week,
        "users_change": users_change,
        "reviews_this_week": reviews_this_week,
        "reviews_change": reviews_change,
        "total_reviews": total_reviews,
        # Dados recentes
        "recent_users": recent_users,
    }
    return render(request, "core/admin_dashboard.html", context)


# Views de Gerenciamento de Notícias


@login_required
def admin_news_list_view(request):
    """Listar todas as notícias com filtragem e ordenação"""
    if not request.user.can_moderate:
        messages.error(request, _("Você não tem permissão para acessar esta página."))
        return redirect("core:landing")

    # Obter parâmetros de filtro
    status_filter = request.GET.get("status", "all")
    category_filter = request.GET.get("category", "all")
    search_query = request.GET.get("q", "").strip()

    # Começar com todas as notícias
    news_list = News.objects.select_related("author", "category").order_by(
        "-created_at"
    )

    # Aplicar filtros
    statuses = {
        "published": News.PUBLISHED,
        "draft": News.DRAFT,
        "archived": News.ARCHIVED,
    }
    if status_filter != "all":
        news_list = news_list.filter(status=statuses.get(status_filter, status_filter))

    if category_filter != "all":
        news_list = news_list.filter(category__name=category_filter)

    if search_query:
        news_list = news_list.filter(title__icontains=search_query)

    # Obter categorias para o filtro
    categories = NewsCategory.objects.all()

    # Obter contagens para estatísticas
    total_count = News.objects.count()
    published_count = News.objects.filter(status=News.PUBLISHED).count()
    draft_count = News.objects.filter(status=News.DRAFT).count()
    archived_count = News.objects.filter(status=News.ARCHIVED).count()

    context = {
        "news_list": news_list,
        "categories": categories,
        "status_filter": status_filter,
        "category_filter": category_filter,
        "search_query": search_query,
        "total_count": total_count,
        "published_count": published_count,
        "draft_count": draft_count,
        "archived_count": archived_count,
    }
    return render(request, "core/admin/news_list.html", context)


@login_required
def admin_news_create_view(request):
    """Criar uma nova notícia/evento"""
    if not request.user.can_moderate:
        messages.error(request, _("Você não tem permissão para acessar esta página."))
        return redirect("core:landing")

    if request.method == "POST":
        form = NewsForm(request.POST, request.FILES)
        if form.is_valid():
            news = form.save(commit=False)
            news.author = request.user
            news.save()
            messages.success(
                request,
                _('Evento "%(title)s" criado com sucesso!') % {"title": news.title},
            )
            return redirect("core:admin_news_list")
    else:
        event = NewsCategory.objects.filter(name=NewsCategory.EVENT).first()
        form = NewsForm(initial={"category": event})

    context = {
        "form": form,
        "title": _("Criar novo evento"),
        "submit_text": _("Criar"),
    }
    return render(request, "core/admin/news_form.html", context)


@login_required
def admin_news_edit_view(request, pk):
    """Editar uma notícia/evento existente"""
    if not request.user.can_moderate:
        messages.error(request, _("Você não tem permissão para acessar esta página."))
        return redirect("core:landing")

    news = get_object_or_404(News, pk=pk)

    if request.method == "POST":
        form = NewsForm(request.POST, request.FILES, instance=news)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                _('Evento "%(title)s" atualizado com sucesso!') % {"title": news.title},
            )
            return redirect("core:admin_news_list")
    else:
        form = NewsForm(instance=news)

    context = {
        "form": form,
        "news": news,
        "title": _("Editar: %(title)s") % {"title": news.title},
        "submit_text": _("Salvar Alterações"),
    }
    return render(request, "core/admin/news_form.html", context)


@login_required
def admin_news_delete_view(request, pk):
    """Excluir uma notícia/evento"""
    if not request.user.can_moderate:
        messages.error(request, _("Você não tem permissão para acessar esta página."))
        return redirect("core:landing")

    news = get_object_or_404(News, pk=pk)

    if request.method == "POST":
        news_title = news.title
        news.delete()
        messages.success(
            request,
            _('Evento "%(news_title)s" excluído com sucesso.')
            % {"news_title": news_title},
        )
        return redirect("core:admin_news_list")

    context = {"news": news}
    return render(request, "core/admin/news_delete_confirm.html", context)


@login_required
@require_POST
def admin_news_bulk_view(request):
    """Publicar, arquivar ou excluir vários eventos de uma vez."""
    if not request.user.can_moderate:
        messages.error(request, _("Você não tem permissão para acessar esta página."))
        return redirect("core:landing")

    destination = safe_next(request, reverse("core:admin_news_list"))
    action = request.POST.get("action")
    ids = [i for i in request.POST.getlist("ids") if i.isdigit()]
    if not ids:
        messages.error(request, _("Selecione ao menos um evento."))
        return redirect(destination)

    items = News.objects.filter(pk__in=ids)
    if action == "publish":
        items = items.exclude(status=News.PUBLISHED)
        count = 0
        for item in items:
            item.status = News.PUBLISHED
            item.save()
            count += 1
        message = ngettext(
            "%(count)d evento publicado", "%(count)d eventos publicados", count
        )
    elif action == "archive":
        items = items.exclude(status=News.ARCHIVED)
        count = 0
        for item in items:
            item.status = News.ARCHIVED
            item.save()
            count += 1
        message = ngettext(
            "%(count)d evento arquivado", "%(count)d eventos arquivados", count
        )
    elif action == "delete":
        count = items.count()
        items.delete()
        message = ngettext(
            "%(count)d evento excluído", "%(count)d eventos excluídos", count
        )
    else:
        messages.error(request, _("Ação inválida."))
        return redirect(destination)
    messages.success(request, message % {"count": count})
    return redirect(destination)


# Triagem de eventos encontrados pelo crawler


def _triage_context(bound_form=None):
    pending = list(
        EventCandidate.objects.filter(status=EventCandidate.PENDING).select_related(
            "possible_duplicate"
        )
    )
    candidates = []
    for c in pending:
        if bound_form is not None and bound_form.instance.pk == c.pk:
            form = bound_form
        else:
            form = EventCandidateForm(instance=c, prefix=f"c{c.pk}")
        siblings = [
            o for o in pending if o.pk != c.pk and event_crawler.same_event(c, o)
        ]
        candidates.append((c, form, siblings))
    recent = (
        EventCandidate.objects.exclude(status=EventCandidate.PENDING)
        .select_related("news", "reviewed_by")
        .order_by("-reviewed_at")[:10]
    )
    return {"candidates": candidates, "recent": recent}


@login_required
def admin_event_triage_view(request):
    if not request.user.can_moderate:
        messages.error(request, _("Você não tem permissão para acessar esta página."))
        return redirect("core:landing")
    return render(request, "core/admin/event_triage.html", _triage_context())


@login_required
@require_POST
def admin_event_triage_action_view(request, pk):
    if not request.user.can_moderate:
        messages.error(request, _("Você não tem permissão para acessar esta página."))
        return redirect("core:landing")

    candidate = get_object_or_404(EventCandidate, pk=pk, status=EventCandidate.PENDING)
    if request.POST.get("action") == "reject":
        event_crawler.reject(candidate, request.user)
        messages.info(
            request, _('"%(title)s" foi descartado.') % {"title": candidate.title}
        )
        return redirect("core:admin_event_triage")

    form = EventCandidateForm(request.POST, instance=candidate, prefix=f"c{pk}")
    if not form.is_valid():
        messages.error(
            request, _('Revise os campos de "%(title)s".') % {"title": candidate.title}
        )
        return render(
            request, "core/admin/event_triage.html", _triage_context(form), status=400
        )

    news = event_crawler.approve(form.save(), request.user)
    messages.success(
        request, _('"%(title)s" publicado na agenda.') % {"title": news.title}
    )
    return redirect("core:admin_event_triage")


@login_required
@require_POST
def admin_event_triage_bulk_view(request):
    """Descartar vários candidatos de uma vez."""
    if not request.user.can_moderate:
        messages.error(request, _("Você não tem permissão para acessar esta página."))
        return redirect("core:landing")

    ids = [i for i in request.POST.getlist("ids") if i.isdigit()]
    if not ids:
        messages.error(request, _("Selecione ao menos um evento."))
    elif request.POST.get("action") == "reject":
        count = event_crawler.reject_many(ids, request.user)
        messages.success(
            request,
            ngettext(
                "%(count)d evento descartado", "%(count)d eventos descartados", count
            )
            % {"count": count},
        )
    else:
        messages.error(request, _("Ação inválida."))
    return redirect("core:admin_event_triage")


@login_required
@require_POST
def admin_event_crawl_view(request):
    if not request.user.can_moderate:
        messages.error(request, _("Você não tem permissão para acessar esta página."))
        return redirect("core:landing")
    try:
        created = event_crawler.store_candidates(event_crawler.fetch_prefeitura_posts())
    except Exception:
        logger.exception("Busca manual de eventos falhou")
        messages.error(request, _("Não foi possível consultar a Prefeitura agora."))
    else:
        messages.success(
            request,
            _("%(created)s evento(s) novo(s) para triagem.") % {"created": created},
        )
    return redirect("core:admin_event_triage")
