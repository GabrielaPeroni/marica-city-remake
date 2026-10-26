from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _

from .forms import UserRegistrationForm
from .models import User


def register_view(request):
    if request.user.is_authenticated:
        return redirect("core:landing")

    if request.method == "POST":
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(
                request, _("Cadastro realizado com sucesso! Bem-vindo ao MaricaCity.")
            )
            return redirect("core:landing")
    else:
        form = UserRegistrationForm()

    context = {
        "form": form,
        "google_client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
    }
    return render(request, "accounts/register.html", context)


def login_view(request):
    """
    Endpoint AJAX de login para autenticação baseada em modal
    Retorna resposta JSON com mensagens de sucesso/erro
    """
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        if not username or not password:
            return JsonResponse(
                {
                    "success": False,
                    "error": _("Por favor, preencha todos os campos."),
                },
                status=400,
            )

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return JsonResponse(
                {
                    "success": True,
                    "message": _("Bem-vindo de volta, %(username)s!")
                    % {"username": user.username},
                    "username": user.username,
                }
            )
        # authenticate() devolve None para contas inativas; só revelamos a
        # desativação a quem acertou a senha.
        inactive = User.objects.filter(username=username, is_active=False).first()
        if inactive and inactive.check_password(password):
            return JsonResponse(
                {
                    "success": False,
                    "error": _(
                        "Sua conta foi desativada. Entre em contato com o administrador."
                    ),
                },
                status=403,
            )

        return JsonResponse(
            {
                "success": False,
                "error": _("Nome de usuário ou senha incorretos."),
            },
            status=401,
        )

    # Requisição GET - não permitida para endpoint AJAX
    return JsonResponse(
        {"success": False, "error": _("Método não permitido")}, status=405
    )


@login_required
def logout_view(request):
    logout(request)
    messages.success(request, _("Você saiu com sucesso."))

    # Redirect to the referring page or home
    next_url = request.GET.get("next") or request.META.get("HTTP_REFERER")
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(next_url)
    return redirect("core:landing")


# Views de Gerenciamento de Usuários Admin
@login_required
def user_management_view(request):
    """View de administração para gerenciar todos os usuários"""
    if not request.user.can_moderate:
        messages.error(request, _("Você não tem permissão para acessar esta página."))
        return redirect("core:landing")

    # Obter parâmetros de filtro
    role_filter = request.GET.get("role", "")  # Alterado de user_type para role
    status_filter = request.GET.get("status", "")
    search_query = request.GET.get("q", "")

    # Queryset base com estatísticas
    users = User.objects.annotate(
        places_count=Count("places", distinct=True),
        reviews_count=Count("place_reviews_written", distinct=True),
    ).select_related()

    # Aplicar filtros
    if role_filter == "staff":
        users = users.filter(is_staff=True)
    elif role_filter == "regular":
        users = users.filter(is_staff=False)

    if status_filter == "active":
        users = users.filter(is_active=True)
    elif status_filter == "inactive":
        users = users.filter(is_active=False)

    if search_query:
        users = users.filter(
            Q(username__icontains=search_query)
            | Q(email__icontains=search_query)
            | Q(first_name__icontains=search_query)
            | Q(last_name__icontains=search_query)
        )

    # Obter estatísticas
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    staff_users = User.objects.filter(is_staff=True).count()
    regular_users = User.objects.filter(is_staff=False).count()

    context = {
        "users": users.order_by("-created_at"),
        "total_users": total_users,
        "active_users": active_users,
        "staff_users": staff_users,
        "regular_users": regular_users,
        "role_filter": role_filter,
        "status_filter": status_filter,
        "search_query": search_query,
    }
    return render(request, "accounts/user_management.html", context)


@login_required
def user_update_type_view(request, user_id):
    """Alterna o status de staff do usuário"""
    if not request.user.can_moderate:
        return JsonResponse({"success": False, "error": _("Sem permissão")}, status=403)

    if request.method != "POST":
        return JsonResponse(
            {"success": False, "error": _("Método não permitido")}, status=405
        )

    user = get_object_or_404(User, id=user_id)

    # Prevenir alteração do próprio status de staff
    if user == request.user:
        return JsonResponse(
            {
                "success": False,
                "error": _("Você não pode alterar seu próprio status"),
            },
            status=400,
        )

    # Alternar status de staff
    user.is_staff = not user.is_staff
    user.save()

    role_display = _("Staff") if user.is_staff else _("Regular")
    messages.success(
        request,
        _("Status de %(username)s alterado para %(role_display)s.")
        % {"username": user.username, "role_display": role_display},
    )
    return JsonResponse(
        {
            "success": True,
            "message": _("Status de usuário atualizado"),
            "role_display": role_display,
            "is_staff": user.is_staff,
        }
    )


@login_required
def user_toggle_status_view(request, user_id):
    """Alterna o status ativo do usuário"""
    if not request.user.can_moderate:
        return JsonResponse({"success": False, "error": _("Sem permissão")}, status=403)

    if request.method != "POST":
        return JsonResponse(
            {"success": False, "error": _("Método não permitido")}, status=405
        )

    user = get_object_or_404(User, id=user_id)

    # Prevenir desativação da própria conta
    if user == request.user:
        return JsonResponse(
            {"success": False, "error": _("Você não pode desativar sua própria conta")},
            status=400,
        )

    user.is_active = not user.is_active
    user.save()

    status_text = "ativado" if user.is_active else "desativado"
    messages.success(
        request,
        _("Usuário %(username)s %(status_text)s com sucesso.")
        % {"username": user.username, "status_text": status_text},
    )

    return JsonResponse(
        {
            "success": True,
            "is_active": user.is_active,
            "message": _("Usuário %(status_text)s") % {"status_text": status_text},
        }
    )


@login_required
def user_delete_view(request, user_id):
    """Excluir conta de usuário"""
    if not request.user.can_moderate:
        messages.error(request, _("Você não tem permissão para excluir usuários."))
        return redirect("accounts:user_management")

    user = get_object_or_404(User, id=user_id)

    # Prevenir exclusão da própria conta
    if user == request.user:
        messages.error(request, _("Você não pode excluir sua própria conta."))
        return redirect("accounts:user_management")

    if request.method == "POST":
        username = user.username
        user.delete()
        messages.success(
            request,
            _("Usuário %(username)s excluído com sucesso.") % {"username": username},
        )
        return redirect("accounts:user_management")

    context = {"user_to_delete": user}
    return render(request, "accounts/user_delete_confirm.html", context)
