from django.contrib import admin

from .models import Category, Favorite, Place, PlaceApproval, PlaceImage, PlaceReview


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "slug",
        "display_order",
        "is_active",
        "active_places_count",
        "created_at",
    )

    list_filter = ("is_active", "created_at")

    search_fields = ("name", "slug", "description")

    readonly_fields = ("created_at", "updated_at")

    prepopulated_fields = {"slug": ("name",)}

    fieldsets = (
        ("Informações Básicas", {"fields": ("name", "slug", "description", "icon")}),
        ("Configurações de Exibição", {"fields": ("display_order", "is_active")}),
        (
            "Datas e Horários",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )


class PlaceImageInline(admin.TabularInline):
    model = PlaceImage
    extra = 1
    fields = ("image", "caption", "is_primary", "display_order")
    readonly_fields = ("uploaded_at",)


@admin.register(Place)
class PlaceAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        if not change:  # Se estiver criando novo objeto
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def approve_places(self, request, queryset):
        """Aprovar lugares selecionados"""
        count = 0
        for place in queryset:
            if not place.is_approved:
                place.is_approved = True
                place.save()
                # Criar registro de aprovação
                PlaceApproval.objects.create(
                    place=place,
                    reviewer=request.user,
                    action="APPROVE",
                    comments="Aprovado via ação em massa no admin",
                )
                count += 1
        self.message_user(request, f"{count} lugar(es) aprovado(s) com sucesso.")

    approve_places.short_description = "Aprovar lugares selecionados"

    def revoke_approval(self, request, queryset):
        """Revogar aprovação de lugares selecionados"""
        count = 0
        for place in queryset:
            if place.is_approved:
                place.is_approved = False
                place.save()
                # Criar registro de revogação
                PlaceApproval.objects.create(
                    place=place,
                    reviewer=request.user,
                    action="REJECT",
                    comments="Aprovação revogada via ação em massa no admin",
                )
                count += 1
        self.message_user(
            request, f"{count} lugar(es) teve(tiveram) aprovação revogada."
        )

    revoke_approval.short_description = "Revogar aprovação de lugares selecionados"

    inlines = [PlaceImageInline]

    list_display = ("name", "created_by", "is_approved", "is_active", "created_at")

    list_filter = ("is_approved", "is_active", "categories", "created_at", "updated_at")

    search_fields = ("name", "description", "address", "created_by__username")

    readonly_fields = ("created_at", "updated_at", "created_by")

    actions = ["approve_places", "revoke_approval"]

    fieldsets = (
        (
            "Informações Básicas",
            {"fields": ("name", "description", "address", "categories")},
        ),
        (
            "Localização",
            {"fields": ("latitude", "longitude"), "classes": ("collapse",)},
        ),
        ("Status", {"fields": ("is_approved", "is_active")}),
        (
            "Metadados",
            {
                "fields": ("created_by", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(PlaceImage)
class PlaceImageAdmin(admin.ModelAdmin):
    list_display = ("place", "caption", "is_primary", "display_order", "uploaded_at")

    list_filter = ("is_primary", "uploaded_at", "place")

    search_fields = ("place__name", "caption")

    readonly_fields = ("uploaded_at",)

    fieldsets = (
        ("Informações da Imagem", {"fields": ("place", "image", "caption")}),
        ("Configurações de Exibição", {"fields": ("is_primary", "display_order")}),
        ("Data e Horário", {"fields": ("uploaded_at",)}),
    )


@admin.register(PlaceApproval)
class PlaceApprovalAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        if not change:  # Se estiver criando novo objeto
            obj.reviewer = request.user
        super().save_model(request, obj, form, change)

    list_display = ("place", "action", "reviewer", "reviewed_at")

    list_filter = ("action", "reviewed_at", "reviewer")

    search_fields = ("place__name", "reviewer__username", "comments")

    readonly_fields = ("reviewed_at",)

    fieldsets = (
        (
            "Informações da Revisão",
            {"fields": ("place", "action", "reviewer", "comments")},
        ),
        ("Data e Horário", {"fields": ("reviewed_at",)}),
    )


@admin.register(PlaceReview)
class PlaceReviewAdmin(admin.ModelAdmin):
    """Administração de Avaliações de Lugares - acesso CRUD completo para administradores"""

    list_display = ("place", "user", "rating", "created_at", "get_comment_preview")

    list_filter = ("rating", "created_at", "updated_at")

    search_fields = ("place__name", "user__username", "comment")

    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        (
            "Informações da Avaliação",
            {"fields": ("place", "user", "rating", "comment")},
        ),
        ("Datas e Horários", {"fields": ("created_at", "updated_at")}),
    )

    def get_comment_preview(self, obj):
        """Mostrar os primeiros 50 caracteres do comentário"""
        return obj.comment[:50] + "..." if len(obj.comment) > 50 else obj.comment

    get_comment_preview.short_description = "Prévia do Comentário"


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    """Administração de Favoritos - gerenciar lugares salvos pelos usuários"""

    list_display = ("user", "place", "created_at")

    list_filter = ("created_at", "place")

    search_fields = ("user__username", "place__name")

    readonly_fields = ("created_at",)

    fieldsets = (
        ("Informações do Favorito", {"fields": ("user", "place")}),
        ("Data e Horário", {"fields": ("created_at",)}),
    )
