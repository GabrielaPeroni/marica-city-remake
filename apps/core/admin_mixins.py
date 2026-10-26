class TranslationsAdminMixin:
    """Mostra as traduções automáticas (JSON editável) no fim do formulário"""

    def get_fieldsets(self, request, obj=None):
        return [
            *super().get_fieldsets(request, obj),
            (
                "Traduções automáticas",
                {"fields": ["translations"], "classes": ["collapse"]},
            ),
        ]
