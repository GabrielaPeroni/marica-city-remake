from django.contrib import admin

from apps.core.admin_mixins import TranslationsAdminMixin

from .models import EventCandidate, News, NewsCategory


@admin.register(NewsCategory)
class NewsCategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "icon", "description"]
    search_fields = ["name", "description"]
    ordering = ["name"]


@admin.register(News)
class NewsAdmin(TranslationsAdminMixin, admin.ModelAdmin):
    list_display = [
        "title",
        "category",
        "status",
        "publish_date",
        "is_featured",
        "view_count",
        "author",
    ]
    list_filter = ["status", "category", "is_featured", "publish_date", "created_at"]
    search_fields = ["title", "content", "excerpt"]
    prepopulated_fields = {"slug": ("title",)}
    date_hierarchy = "publish_date"
    ordering = ["-publish_date", "-created_at"]

    fieldsets = [
        (
            "Conteúdo Principal",
            {
                "fields": ["title", "slug", "category", "excerpt", "content"],
                "description": "Informações básicas da notícia/evento",
            },
        ),
        (
            "Mídia",
            {
                "fields": ["featured_image", "image_caption"],
            },
        ),
        (
            "Detalhes do Evento",
            {
                "fields": ["event_date", "event_end_date", "event_location"],
                "classes": ["collapse"],
                "description": "Preencha estes campos apenas se a categoria for 'Evento'",
            },
        ),
        (
            "Opções de Publicação",
            {
                "fields": [
                    "status",
                    "is_featured",
                    "author",
                    "publish_date",
                    "source_name",
                    "source_url",
                ],
                "description": "A data de publicação é definida automaticamente ao publicar",
            },
        ),
        (
            "Metadados",
            {
                "fields": ["view_count", "created_at", "updated_at"],
                "classes": ["collapse"],
            },
        ),
    ]

    readonly_fields = ["publish_date", "created_at", "updated_at", "view_count"]

    def save_model(self, request, obj, form, change):
        """Definir autor como usuário atual se estiver criando nova notícia"""
        if not change:
            obj.author = request.user
        super().save_model(request, obj, form, change)


@admin.register(EventCandidate)
class EventCandidateAdmin(admin.ModelAdmin):
    list_display = ["title", "event_date", "event_location", "score", "status"]
    list_filter = ["status", "source"]
    search_fields = ["title", "summary"]
    readonly_fields = ["source", "source_id", "source_url", "news", "reviewed_by"]
