"""
Views de API para o aplicativo explore
Fornece endpoints JSON para integração com mapas e outros recursos
"""

from django.db.models import Avg, Count
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from .models import Place


@require_GET
def map_data_api(request):
    """
    Endpoint de API que retorna todos os lugares aprovados com coordenadas em formato JSON
    Usado pelo mapa interativo da página inicial
    """
    # Obter todos os lugares aprovados com coordenadas
    places = (
        Place.objects.filter(
            is_approved=True,
            is_active=True,
            latitude__isnull=False,
            longitude__isnull=False,
        )
        .prefetch_related("images", "categories")
        # Aggregate rating/review count in SQL instead of one query per
        # place in the loop below (distinct=True avoids join fan-out).
        .annotate(
            avg_rating=Avg("reviews__rating"),
            rating_count=Count("reviews", distinct=True),
        )
        .order_by("-created_at")
    )

    # Construir dados de resposta
    places_data = []
    for place in places:
        # Obter imagem primária ou primeira imagem
        primary_image = place.primary_image
        image_url = primary_image.image.url if primary_image else None

        # Obter primeira categoria para ícone/cor (usa o cache do prefetch)
        categories = list(place.categories.all())
        first_category = categories[0] if categories else None
        category_name = first_category.name if first_category else "Outros"
        category_icon = first_category.icon if first_category else "📍"

        places_data.append(
            {
                "id": place.id,
                "name": place.name,
                "description": (
                    place.description[:100] + "..."
                    if len(place.description) > 100
                    else place.description
                ),
                "latitude": float(place.latitude),
                "longitude": float(place.longitude),
                "image_url": image_url,
                "category": category_name,
                "category_icon": category_icon,
                "url": f"/explore/place/{place.id}/",
                "rating": round(place.avg_rating, 1) if place.avg_rating else None,
                "review_count": place.rating_count,
            }
        )

    return JsonResponse({"places": places_data, "count": len(places_data)})


@require_GET
def places_by_ids_api(request):
    """
    Endpoint de API que retorna detalhes de lugares para IDs fornecidos
    Usado pela página de favoritos para usuários anônimos
    """
    # Obter IDs separados por vírgula do parâmetro de consulta
    ids_param = request.GET.get("ids", "")

    if not ids_param:
        return JsonResponse({"places": [], "count": 0})

    # Analisar IDs
    try:
        place_ids = [int(id.strip()) for id in ids_param.split(",") if id.strip()]
    except ValueError:
        return JsonResponse({"error": "Formato de ID inválido"}, status=400)

    # Obter lugares
    places = (
        Place.objects.filter(
            id__in=place_ids,
            is_approved=True,
            is_active=True,
        )
        .prefetch_related("images", "categories", "created_by")
        .annotate(
            avg_rating=Avg("reviews__rating"),
            rating_count=Count("reviews", distinct=True),
        )
        .order_by("-created_at")
    )

    # Construir dados de resposta
    places_data = []
    for place in places:
        # Obter imagem primária ou primeira imagem
        primary_image = place.primary_image
        image_url = primary_image.image.url if primary_image else None

        # Obter categorias
        categories = [
            {
                "name": cat.name,
                "icon": cat.icon if cat.icon else "",
                "slug": cat.slug,
            }
            for cat in place.categories.all()
        ]

        places_data.append(
            {
                "id": place.id,
                "name": place.name,
                "description": place.description,
                "image_url": image_url,
                "categories": categories,
                "url": f"/explore/place/{place.id}/",
                "rating": round(place.avg_rating, 1) if place.avg_rating else None,
                "review_count": place.rating_count,
            }
        )

    return JsonResponse({"places": places_data, "count": len(places_data)})
