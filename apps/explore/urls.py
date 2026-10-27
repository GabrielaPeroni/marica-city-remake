from django.urls import path

from . import api, views

app_name = "explore"

urlpatterns = [
    path("", views.explore_view, name="explore"),
    # API endpoints
    path("api/map-data/", api.map_data_api, name="map_data_api"),
    path("api/places-by-ids/", api.places_by_ids_api, name="places_by_ids_api"),
    path("category/<slug:slug>/", views.category_detail_view, name="category_detail"),
    path("place/<int:pk>/", views.place_detail_view, name="place_detail"),
    path("place/create/", views.place_create_view, name="place_create"),
    path("place/<int:pk>/edit/", views.place_update_view, name="place_edit"),
    path("place/<int:pk>/delete/", views.place_delete_view, name="place_delete"),
    # Admin approval URLs
    path("admin/approval-queue/", views.approval_queue_view, name="approval_queue"),
    path(
        "admin/place/<int:pk>/approve/", views.approve_place_view, name="approve_place"
    ),
    path("admin/place/<int:pk>/reject/", views.reject_place_view, name="reject_place"),
    path("admin/places/bulk/", views.bulk_places_view, name="bulk_places"),
    path("admin/backlog/", views.backlog_view, name="backlog"),
    # Review URLs
    path(
        "place/<int:place_pk>/review/create/",
        views.review_create_view,
        name="review_create",
    ),
    path("review/<int:pk>/edit/", views.review_edit_view, name="review_edit"),
    path("review/<int:pk>/delete/", views.review_delete_view, name="review_delete"),
    # Favorites URLs
    path(
        "place/<int:pk>/favorite/toggle/",
        views.toggle_favorite_view,
        name="toggle_favorite",
    ),
    path("favorites/", views.favorites_list_view, name="favorites"),
    path("favorites/sync/", views.sync_favorites_view, name="sync_favorites"),
    path("favorites/list/", views.favorites_api_list_view, name="favorites_api_list"),
]
