from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET

from apps.accounts.models import User
from apps.explore.models import Category, Place, PlaceReview
from apps.news.forms import NewsForm
from apps.news.models import News, NewsCategory


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

    # Lugares em alta (mais populares nos últimos 7 dias)
    day_range = timezone.now() - timedelta(days=7)
    trending_places = (
        Place.objects.filter(
            is_approved=True, is_active=True, created_at__gte=day_range
        )
        .prefetch_related("images", "categories")
        .order_by("-created_at")[:4]
    )

    categories = Category.objects.filter(is_active=True).order_by("display_order")[:8]

    context = {
        "featured_places": featured_places,
        "trending_places": trending_places,
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
        messages.error(request, "Você não tem permissão para acessar esta página.")
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
        messages.error(request, "Você não tem permissão para acessar esta página.")
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
    if status_filter != "all":
        news_list = news_list.filter(status=status_filter)

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
        messages.error(request, "Você não tem permissão para acessar esta página.")
        return redirect("core:landing")

    if request.method == "POST":
        form = NewsForm(request.POST, request.FILES)
        if form.is_valid():
            news = form.save(commit=False)
            news.author = request.user
            news.save()
            messages.success(request, f'Notícia "{news.title}" criada com sucesso!')
            return redirect("core:admin_news_list")
    else:
        form = NewsForm()

    context = {
        "form": form,
        "title": "Criar Nova Notícia/Evento",
        "submit_text": "Criar",
    }
    return render(request, "core/admin/news_form.html", context)


@login_required
def admin_news_edit_view(request, pk):
    """Editar uma notícia/evento existente"""
    if not request.user.can_moderate:
        messages.error(request, "Você não tem permissão para acessar esta página.")
        return redirect("core:landing")

    from django.shortcuts import get_object_or_404

    news = get_object_or_404(News, pk=pk)

    if request.method == "POST":
        form = NewsForm(request.POST, request.FILES, instance=news)
        if form.is_valid():
            form.save()
            messages.success(request, f'Notícia "{news.title}" atualizada com sucesso!')
            return redirect("core:admin_news_list")
    else:
        form = NewsForm(instance=news)

    context = {
        "form": form,
        "news": news,
        "title": f"Editar: {news.title}",
        "submit_text": "Salvar Alterações",
    }
    return render(request, "core/admin/news_form.html", context)


@login_required
def admin_news_delete_view(request, pk):
    """Excluir uma notícia/evento"""
    if not request.user.can_moderate:
        messages.error(request, "Você não tem permissão para acessar esta página.")
        return redirect("core:landing")

    from django.shortcuts import get_object_or_404

    news = get_object_or_404(News, pk=pk)

    if request.method == "POST":
        news_title = news.title
        news.delete()
        messages.success(request, f'Notícia "{news_title}" excluída com sucesso.')
        return redirect("core:admin_news_list")

    context = {"news": news}
    return render(request, "core/admin/news_delete_confirm.html", context)
