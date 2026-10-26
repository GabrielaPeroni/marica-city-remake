from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.landing_view, name="landing"),
    path("sobre/", views.about_view, name="about"),
    path("planeje-sua-visita/", views.visit_view, name="visit"),
    path("painel-admin/", views.admin_dashboard_view, name="admin_dashboard"),
    path("painel-admin/noticias/", views.admin_news_list_view, name="admin_news_list"),
    path(
        "painel-admin/noticias/criar/",
        views.admin_news_create_view,
        name="admin_news_create",
    ),
    path(
        "painel-admin/noticias/<int:pk>/editar/",
        views.admin_news_edit_view,
        name="admin_news_edit",
    ),
    path(
        "painel-admin/noticias/<int:pk>/excluir/",
        views.admin_news_delete_view,
        name="admin_news_delete",
    ),
    path(
        "painel-admin/eventos/triagem/",
        views.admin_event_triage_view,
        name="admin_event_triage",
    ),
    path(
        "painel-admin/eventos/triagem/<int:pk>/",
        views.admin_event_triage_action_view,
        name="admin_event_triage_action",
    ),
    path(
        "painel-admin/eventos/buscar/",
        views.admin_event_crawl_view,
        name="admin_event_crawl",
    ),
]
