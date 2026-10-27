import re
from datetime import timedelta
from uuid import uuid4

from django.db.models import Count, Q
from django.utils import timezone

from apps.core.utils import is_speculative

from .models import Place, PlaceVisit

CONSENT_COOKIE = "mc_consent"
VISITOR_COOKIE = "mc_visitor"
VISITOR_MAX_AGE = 365 * 24 * 60 * 60


def record_visit(request, response, place):
    """Conta a visita ao lugar se o visitante aceitou cookies; senão apaga o identificador."""
    if request.COOKIES.get(CONSENT_COOKIE) != "accepted":
        if VISITOR_COOKIE in request.COOKIES:
            response.delete_cookie(VISITOR_COOKIE)
        return
    user = request.user
    if is_speculative(request) or not (place.is_approved and place.is_active):
        return
    if user.is_authenticated and (user.can_moderate or place.created_by_id == user.pk):
        return

    visitor = request.COOKIES.get(VISITOR_COOKIE, "")
    if not re.fullmatch(r"[0-9a-f]{32}", visitor):
        visitor = uuid4().hex
        response.set_cookie(
            VISITOR_COOKIE,
            visitor,
            max_age=VISITOR_MAX_AGE,
            httponly=True,
            samesite="Lax",
            secure=request.is_secure(),
        )
    PlaceVisit.objects.get_or_create(
        place=place, visitor=visitor, date=timezone.localdate()
    )


def most_visited(days=7, limit=4):
    """Lugares públicos com mais visitas nos últimos `days` dias."""
    since = timezone.localdate() - timedelta(days=days)
    return (
        Place.objects.filter(is_approved=True, is_active=True)
        .annotate(
            recent_visits=Count(
                "visits", filter=Q(visits__date__gt=since), distinct=True
            )
        )
        .with_ratings()
        .filter(recent_visits__gt=0)
        .order_by("-recent_visits", "-created_at")
        .prefetch_related("images", "categories")[:limit]
    )
