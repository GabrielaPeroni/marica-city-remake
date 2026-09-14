from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from django_ratelimit.decorators import ratelimit

from .forms import PlaceForm, PlaceImageFormSet, PlaceReviewForm
from .models import Category, Favorite, Place, PlaceApproval, PlaceReview


def explore_view(request):
    """Página de exploração com categorias e todos os lugares com pesquisa"""

    # Obter todas as categorias ativas com contagens de lugares
    categories = Category.objects.filter(is_active=True).order_by("display_order")

    # Obter consulta de pesquisa
    search_query = request.GET.get("q", "").strip()

    # Obter parâmetro de ordenação
    sort_by = request.GET.get("sort", "-created_at")
    valid_sorts = {
        "-created_at": "-created_at",
        "name": "name",
        "-name": "-name",
    }
    sort_order = valid_sorts.get(sort_by, "-created_at")

    # Base queryset: all approved and active places
    base_query = Q(is_approved=True, is_active=True)

    # If user is authenticated, also include their own pending places
    if request.user.is_authenticated:
        user_pending_query = Q(
            created_by=request.user, is_approved=False, is_active=True
        )
        all_places = Place.objects.filter(base_query | user_pending_query)
    else:
        all_places = Place.objects.filter(base_query)

    # Aplicar filtro de pesquisa se houver consulta
    if search_query:
        all_places = all_places.filter(
            Q(name__icontains=search_query)
            | Q(description__icontains=search_query)
            | Q(categories__name__icontains=search_query)
        ).distinct()

    all_places = all_places.prefetch_related("images", "categories").order_by(
        sort_order
    )

    context = {
        "categories": categories,
        "all_places": all_places,
        "current_sort": sort_by,
    }
    return render(request, "explore/explore.html", context)


def category_detail_view(request, slug):
    """Página de detalhes da categoria com todos os lugares na categoria"""

    # Obter a categoria ou 404
    category = get_object_or_404(Category, slug=slug, is_active=True)

    # Obter parâmetro de ordenação
    sort_by = request.GET.get("sort", "-created_at")
    valid_sorts = {
        "-created_at": "-created_at",
        "name": "name",
        "-name": "-name",
    }
    sort_order = valid_sorts.get(sort_by, "-created_at")

    # Obter todos os lugares aprovados e ativos nesta categoria
    places = (
        Place.objects.filter(categories=category, is_approved=True, is_active=True)
        .prefetch_related("images", "categories", "created_by")
        .order_by(sort_order)
    )

    # Obter todas as categorias para navegação
    all_categories = Category.objects.filter(is_active=True).order_by("display_order")

    context = {
        "category": category,
        "places": places,
        "all_categories": all_categories,
        "current_sort": sort_by,
    }
    return render(request, "explore/category_detail.html", context)


def place_detail_view(request, pk):
    """Página de detalhes do lugar individual"""

    # Obter o lugar ou 404 (mostrar apenas lugares aprovados e ativos para não-moderadores)
    if request.user.is_authenticated:
        # Todos os usuários autenticados podem ver seus próprios lugares não aprovados
        place = get_object_or_404(
            Place.objects.prefetch_related("images", "categories"), pk=pk
        )
        # Mas usuários regulares só podem ver lugares aprovados E ativos
        # (a menos que sejam o próprio criador ou um moderador)
        if (
            place.created_by != request.user
            and not request.user.can_moderate
            and not (place.is_approved and place.is_active)
        ):
            place = get_object_or_404(Place, pk=pk, is_approved=True, is_active=True)
    else:
        # Usuários regulares só podem ver lugares aprovados e ativos
        place = get_object_or_404(Place, pk=pk, is_approved=True, is_active=True)

    # Obter lugares relacionados das mesmas categorias
    related_places = (
        Place.objects.filter(
            categories__in=place.categories.all(), is_approved=True, is_active=True
        )
        .exclude(pk=place.pk)
        .distinct()
        .prefetch_related("images", "categories")[:3]
    )

    # Verificar se o usuário pode editar este lugar
    can_edit = False
    if request.user.is_authenticated:
        if request.user.can_moderate or place.created_by == request.user:
            can_edit = True

    # Obter todas as avaliações para este lugar
    reviews = place.reviews.select_related("user").order_by("-created_at")

    # Verificar se o usuário atual já avaliou este lugar
    user_review = None
    if request.user.is_authenticated:
        user_review = reviews.filter(user=request.user).first()

    # Verificar se o lugar está favoritado pelo usuário atual
    is_favorited = False
    if request.user.is_authenticated:
        is_favorited = Favorite.objects.filter(user=request.user, place=place).exists()

    # Obter contagem de favoritos
    favorites_count = place.favorited_by.count()

    context = {
        "place": place,
        "related_places": related_places,
        "can_edit": can_edit,
        "reviews": reviews,
        "user_review": user_review,
        "is_favorited": is_favorited,
        "favorites_count": favorites_count,
        "GOOGLE_MAPS_API_KEY": settings.GOOGLE_MAPS_API_KEY,
    }
    return render(request, "explore/place_detail.html", context)


@login_required
@ratelimit(key="user", rate="5/h", method="POST", block=True)
def place_create_view(request):
    """Criar um novo lugar (todos os usuários autenticados)"""

    # Verificar se o usuário pode criar lugares
    if not request.user.can_create_places:
        messages.error(request, "Você não tem permissão para criar lugares.")
        return redirect("explore:explore")

    if request.method == "POST":
        form = PlaceForm(request.POST)
        formset = PlaceImageFormSet(request.POST, request.FILES)

        if form.is_valid() and formset.is_valid():
            # Criar o lugar
            place = form.save(commit=False)
            place.created_by = request.user
            place.is_approved = False  # Sempre começa como não aprovado
            place.save()

            # Salvar categorias (relacionamento muitos-para-muitos)
            form.save_m2m()

            # Salvar imagens
            formset.instance = place
            formset.save()

            # Garantir que pelo menos uma imagem seja marcada como primária
            images = place.images.all()
            if images.exists():
                primary_images = images.filter(is_primary=True)
                if not primary_images.exists():
                    # Se nenhuma imagem primária está definida, tornar a primeira como primária
                    first_image = images.first()
                    first_image.is_primary = True
                    first_image.save()
                elif primary_images.count() > 1:
                    # Se houver múltiplas imagens primárias, manter apenas a primeira
                    primary_images.exclude(id=primary_images.first().id).update(
                        is_primary=False
                    )

            messages.success(
                request,
                f'Lugar "{place.name}" criado com sucesso! Ele será revisado por um administrador antes de aparecer no site.',
            )
            return redirect("explore:place_detail", pk=place.pk)
    else:
        form = PlaceForm()
        formset = PlaceImageFormSet()

    context = {
        "form": form,
        "formset": formset,
        "title": "Adicionar Novo Lugar",
        "submit_text": "Enviar para Aprovação",
        "GOOGLE_MAPS_API_KEY": settings.GOOGLE_MAPS_API_KEY,
    }
    return render(request, "explore/place_form.html", context)


@login_required
@ratelimit(key="user", rate="10/h", method="POST", block=True)
def place_update_view(request, pk):
    """Atualizar um lugar existente (apenas proprietário ou administrador)"""

    # Obter o lugar
    place = get_object_or_404(Place, pk=pk)

    # Verificar permissões
    if not (request.user.can_moderate or place.created_by == request.user):
        messages.error(request, "Você não tem permissão para editar este lugar.")
        return redirect("explore:place_detail", pk=place.pk)

    if request.method == "POST":
        form = PlaceForm(request.POST, instance=place)
        formset = PlaceImageFormSet(request.POST, request.FILES, instance=place)

        if form.is_valid() and formset.is_valid():
            # Salvar o lugar
            updated_place = form.save()

            # Salvar imagens
            formset.save()

            # Garantir que pelo menos uma imagem seja marcada como primária
            images = updated_place.images.all()
            if images.exists():
                primary_images = images.filter(is_primary=True)
                if not primary_images.exists():
                    # Se nenhuma imagem primária está definida, tornar a primeira como primária
                    first_image = images.first()
                    first_image.is_primary = True
                    first_image.save()
                elif primary_images.count() > 1:
                    # Se houver múltiplas imagens primárias, manter apenas a primeira
                    primary_images.exclude(id=primary_images.first().id).update(
                        is_primary=False
                    )

            messages.success(
                request, f'Lugar "{updated_place.name}" atualizado com sucesso!'
            )
            return redirect("explore:place_detail", pk=updated_place.pk)
    else:
        form = PlaceForm(instance=place)
        formset = PlaceImageFormSet(instance=place)

    context = {
        "form": form,
        "formset": formset,
        "place": place,
        "title": f"Editar {place.name}",
        "submit_text": "Salvar Alterações",
        "GOOGLE_MAPS_API_KEY": settings.GOOGLE_MAPS_API_KEY,
    }
    return render(request, "explore/place_form.html", context)


@login_required
def place_delete_view(request, pk):
    """Excluir um lugar (apenas proprietário ou administrador)"""

    place = get_object_or_404(Place, pk=pk)

    # Verificar permissões
    if not (request.user.can_moderate or place.created_by == request.user):
        messages.error(request, "Você não tem permissão para excluir este lugar.")
        return redirect("explore:place_detail", pk=place.pk)

    if request.method == "POST":
        place_name = place.name
        place.delete()
        messages.success(request, f'Lugar "{place_name}" foi excluído com sucesso.')
        return redirect("explore:explore")

    # If not POST, redirect back
    return redirect("explore:place_edit", pk=pk)


# Views de aprovação do administrador


@login_required
def approval_queue_view(request):
    """Fila de aprovação do administrador - redireciona para backlog com view=queue"""

    # Verificar se o usuário é administrador
    if not request.user.can_moderate:
        messages.error(request, "Você não tem permissão para acessar esta página.")
        return redirect("explore:explore")

    # Redirecionar para a visualização unificada no modo de fila
    return redirect(reverse("explore:backlog") + "?view=queue")


@login_required
def approve_place_view(request, pk):
    """Aprovar um lugar pendente"""

    # Verificar se o usuário é administrador
    if not request.user.can_moderate:
        messages.error(request, "Você não tem permissão para realizar esta ação.")
        return redirect("explore:explore")

    place = get_object_or_404(Place, pk=pk)

    if request.method == "POST":
        # Criar registro de aprovação
        PlaceApproval.objects.create(
            place=place,
            reviewer=request.user,
            action=PlaceApproval.ActionType.APPROVE,
            comments=request.POST.get("comments", ""),
        )

        messages.success(
            request,
            f'Lugar "{place.name}" foi aprovado com sucesso!',
        )
        return redirect(reverse("explore:backlog") + "?view=queue")

    # Se for GET, redirecionar para detalhes do lugar
    return redirect("explore:place_detail", pk=pk)


@login_required
def reject_place_view(request, pk):
    """Rejeitar um lugar pendente"""

    # Verificar se o usuário é administrador
    if not request.user.can_moderate:
        messages.error(request, "Você não tem permissão para realizar esta ação.")
        return redirect("explore:explore")

    place = get_object_or_404(Place, pk=pk)

    if request.method == "POST":
        reason = request.POST.get("reason", "")
        custom_comments = request.POST.get("comments", "")

        if not reason:
            messages.error(request, "Por favor, selecione um motivo para a rejeição.")
            return redirect("explore:reject_place", pk=pk)

        # Use custom comments if "Outros" is selected, otherwise use the reason
        if reason == "Outros":
            if not custom_comments:
                messages.error(request, "Por favor, especifique o motivo da rejeição.")
                return redirect("explore:reject_place", pk=pk)
            comments = custom_comments
        else:
            comments = reason

        # Criar registro de rejeição
        PlaceApproval.objects.create(
            place=place,
            reviewer=request.user,
            action=PlaceApproval.ActionType.REJECT,
            comments=comments,
        )

        messages.success(
            request,
            f'Lugar "{place.name}" foi removido.',
        )
        return redirect(reverse("explore:backlog") + "?view=queue")

    # If GET request, redirect to backlog (modal handles rejection)
    return redirect("explore:backlog")


@login_required
def backlog_view(request):
    """Backlog do administrador mostrando todos os lugares com filtragem"""

    # Verificar se o usuário é administrador
    if not request.user.can_moderate:
        messages.error(request, "Você não tem permissão para acessar esta página.")
        return redirect("explore:explore")

    # Obter parâmetro de visualização (queue ou history)
    view_mode = request.GET.get("view", "history")

    # Obter parâmetros de filtro
    status_filter = request.GET.get("status", "all")
    category_filter = request.GET.get("category", "all")
    sort_by = request.GET.get("sort", "-created_at")

    # Começar com todos os lugares
    places = Place.objects.select_related("created_by").prefetch_related(
        "images", "categories"
    )

    # Se estiver no modo de fila, mostrar apenas pendentes
    if view_mode == "queue":
        places = places.filter(is_approved=False, is_active=True)
    else:
        # Aplicar filtro de status no modo histórico
        if status_filter == "approved":
            places = places.filter(is_approved=True, is_active=True)
        elif status_filter == "pending":
            places = places.filter(is_approved=False, is_active=True)
        elif status_filter == "rejected":
            places = places.filter(is_active=False)

    # Aplicar filtro de categoria
    if category_filter != "all":
        places = places.filter(categories__slug=category_filter)

    # Aplicar ordenação
    valid_sorts = {
        "-created_at": "-created_at",
        "created_at": "created_at",
        "name": "name",
        "-name": "-name",
    }
    sort_order = valid_sorts.get(sort_by, "-created_at")
    places = places.order_by(sort_order).distinct()

    # Obter todas as categorias para o menu suspenso de filtro
    categories = Category.objects.filter(is_active=True).order_by("name")

    # Obter contagens para cada status
    total_count = Place.objects.count()
    approved_count = Place.objects.filter(is_approved=True, is_active=True).count()
    pending_count = Place.objects.filter(is_approved=False, is_active=True).count()
    rejected_count = Place.objects.filter(is_active=False).count()

    context = {
        "places": places,
        "categories": categories,
        "status_filter": status_filter,
        "category_filter": category_filter,
        "current_sort": sort_by,
        "total_count": total_count,
        "approved_count": approved_count,
        "pending_count": pending_count,
        "rejected_count": rejected_count,
        "view_mode": view_mode,
    }
    return render(request, "explore/admin/backlog.html", context)


# Views de Avaliação


@login_required
def review_create_view(request, place_pk):
    """Criar uma nova avaliação para um lugar"""
    place = get_object_or_404(Place, pk=place_pk, is_approved=True, is_active=True)

    # Verificar se o usuário já avaliou este lugar
    existing_review = PlaceReview.objects.filter(place=place, user=request.user).first()
    if existing_review:
        messages.warning(
            request, "Você já avaliou este lugar. Edite sua avaliação existente."
        )
        return redirect("explore:place_detail", pk=place.pk)

    if request.method == "POST":
        form = PlaceReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.place = place
            review.user = request.user
            review.save()
            messages.success(request, "Avaliação enviada com sucesso!")
            return redirect("explore:place_detail", pk=place.pk)
    else:
        form = PlaceReviewForm()

    context = {"form": form, "place": place}
    return render(request, "explore/review_form.html", context)


@login_required
def review_edit_view(request, pk):
    """Editar uma avaliação existente"""
    review = get_object_or_404(PlaceReview, pk=pk)

    # Verificar permissões: proprietário ou moderador pode editar
    if review.user != request.user and not request.user.can_moderate:
        messages.error(request, "Você não tem permissão para editar esta avaliação.")
        return redirect("explore:place_detail", pk=review.place.pk)

    if request.method == "POST":
        form = PlaceReviewForm(request.POST, instance=review)
        if form.is_valid():
            form.save()
            messages.success(request, "Avaliação atualizada com sucesso!")
            return redirect("explore:place_detail", pk=review.place.pk)
    else:
        form = PlaceReviewForm(instance=review)

    context = {"form": form, "place": review.place, "review": review}
    return render(request, "explore/review_form.html", context)


@login_required
def review_delete_view(request, pk):
    """Excluir uma avaliação"""
    review = get_object_or_404(PlaceReview, pk=pk)

    # Verificar permissões: proprietário ou moderador pode excluir
    if review.user != request.user and not request.user.can_moderate:
        messages.error(request, "Você não tem permissão para excluir esta avaliação.")
        return redirect("explore:place_detail", pk=review.place.pk)

    place_pk = review.place.pk
    if request.method == "POST":
        review.delete()
        messages.success(request, "Avaliação excluída com sucesso!")
        return redirect("explore:place_detail", pk=place_pk)

    context = {"review": review}
    return render(request, "explore/review_delete_confirm.html", context)


# Views de Favoritos


def toggle_favorite_view(request, pk):
    """
    Alternar status de favorito para um lugar (endpoint AJAX)
    Funciona para usuários autenticados e anônimos
    - Usuários autenticados: sincroniza com banco de dados backend
    - Usuários anônimos: apenas no lado do cliente (localStorage)
    """
    if request.method != "POST":
        return JsonResponse({"error": "POST method required"}, status=405)

    place = get_object_or_404(Place, pk=pk, is_approved=True, is_active=True)

    # Para usuários autenticados, sincronizar com banco de dados
    if request.user.is_authenticated:
        favorite = Favorite.objects.filter(user=request.user, place=place).first()

        if favorite:
            # Remover favorito
            favorite.delete()
            is_favorited = False
            message = "Lugar removido dos favoritos"
        else:
            # Adicionar favorito
            Favorite.objects.create(user=request.user, place=place)
            is_favorited = True
            message = "Lugar adicionado aos favoritos"

        # Obter contagem total de favoritos para este lugar
        favorites_count = place.favorited_by.count()

        return JsonResponse(
            {
                "success": True,
                "is_favorited": is_favorited,
                "favorites_count": favorites_count,
                "message": message,
            }
        )
    else:
        # Para usuários anônimos, apenas confirmar a ação
        # A alternância real acontece no localStorage do lado do cliente
        return JsonResponse(
            {
                "success": True,
                "message": "Favorito atualizado",
            }
        )


def favorites_list_view(request):
    """
    Listar todos os favoritos para o usuário atual
    - Usuários autenticados: mostra favoritos do banco de dados
    - Usuários anônimos: página usa JavaScript para carregar do localStorage
    """
    if request.user.is_authenticated:
        # Obter favoritos do banco de dados para usuários autenticados
        favorites = (
            Favorite.objects.filter(user=request.user)
            .select_related("place", "place__created_by")
            .prefetch_related("place__images", "place__categories")
            .order_by("-created_at")
        )

        context = {
            "favorites": favorites,
            "favorites_count": favorites.count(),
            "is_authenticated": True,
        }
    else:
        # Para usuários anônimos, a página usará JavaScript para carregar do localStorage
        context = {
            "favorites": [],
            "favorites_count": 0,
            "is_authenticated": False,
        }

    return render(request, "explore/favorites.html", context)


@login_required
def sync_favorites_view(request):
    """
    Sincronizar favoritos do localStorage para backend (para usuários autenticados)
    Mescla favoritos locais com favoritos do backend
    """
    if request.method != "POST":
        return JsonResponse({"error": "POST method required"}, status=405)

    try:
        import json

        data = json.loads(request.body)
        local_favorites = data.get("favorites", [])

        # Obter favoritos existentes no backend
        existing_favorites = set(
            Favorite.objects.filter(user=request.user).values_list(
                "place_id", flat=True
            )
        )

        # Mesclar: adicionar quaisquer novos favoritos do localStorage ao backend
        new_favorites = []
        for place_id in local_favorites:
            if place_id not in existing_favorites:
                # Verificar se o lugar existe e está aprovado
                try:
                    place = Place.objects.get(pk=place_id, is_approved=True)
                    Favorite.objects.create(user=request.user, place=place)
                    new_favorites.append(place_id)
                except Place.DoesNotExist:
                    continue

        # Obter todos os favoritos (mesclados)
        all_favorites = list(
            Favorite.objects.filter(user=request.user).values_list(
                "place_id", flat=True
            )
        )

        return JsonResponse(
            {
                "success": True,
                "favorites": all_favorites,
                "added": len(new_favorites),
                "message": f"{len(new_favorites)} favoritos sincronizados",
            }
        )

    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@login_required
def favorites_api_list_view(request):
    """
    Endpoint de API para obter lista de IDs de lugares favoritos para usuário autenticado
    Usado pelo JavaScript para sincronizar localStorage com backend ao carregar a página
    """
    favorites = list(
        Favorite.objects.filter(user=request.user).values_list("place_id", flat=True)
    )

    return JsonResponse(
        {
            "success": True,
            "favorites": favorites,
            "count": len(favorites),
        }
    )
