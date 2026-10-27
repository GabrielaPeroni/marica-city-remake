from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.utils.translation import gettext as _


def moderator_required(view):
    """Login obrigatório; quem não modera volta à página inicial com um aviso."""

    @login_required
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.can_moderate:
            messages.error(
                request, _("Você não tem permissão para acessar esta página.")
            )
            return redirect("core:landing")
        return view(request, *args, **kwargs)

    return wrapper
