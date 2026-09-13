from django import forms

from .models import News, NewsCategory


class NewsForm(forms.ModelForm):
    """Form for creating and editing news/events"""

    class Meta:
        model = News
        fields = [
            # Core Content
            "title",
            "category",
            "excerpt",
            "content",
            # Media
            "featured_image",
            "image_caption",
            # Event Details (conditional)
            "event_date",
            "event_end_date",
            "event_location",
            # Publishing Options
            "status",
            "is_featured",
        ]
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Digite o título da notícia/evento",
                }
            ),
            "content": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 10,
                    "placeholder": "Conteúdo completo...",
                }
            ),
            "excerpt": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Resumo curto (até 300 caracteres)",
                    "maxlength": 300,
                }
            ),
            "category": forms.Select(attrs={"class": "form-select"}),
            "featured_image": forms.FileInput(
                attrs={"class": "form-control", "accept": "image/*"}
            ),
            "image_caption": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Legenda da imagem (opcional)",
                }
            ),
            "event_date": forms.DateTimeInput(
                attrs={
                    "class": "form-control",
                    "type": "datetime-local",
                },
                format="%Y-%m-%dT%H:%M",
            ),
            "event_location": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Local do evento (opcional)",
                }
            ),
            "event_end_date": forms.DateTimeInput(
                attrs={
                    "class": "form-control",
                    "type": "datetime-local",
                },
                format="%Y-%m-%dT%H:%M",
            ),
            "status": forms.Select(attrs={"class": "form-select"}),
            "is_featured": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
        labels = {
            "title": "Título",
            "category": "Categoria",
            "excerpt": "Resumo",
            "content": "Conteúdo",
            "featured_image": "Imagem Destacada",
            "image_caption": "Legenda da Imagem",
            "event_date": "Data do Evento",
            "event_end_date": "Data Final do Evento",
            "event_location": "Local do Evento",
            "status": "Status",
            "is_featured": "Destacar",
        }
        help_texts = {
            "category": "Escolha 'Evento' se for um evento com data específica",
            "excerpt": "Deixe em branco para gerar automaticamente do conteúdo",
            "event_date": "Obrigatório apenas para eventos",
            "event_location": "Obrigatório apenas para eventos",
            "status": "A data de publicação será definida automaticamente ao publicar",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Make event fields not required by default
        self.fields["event_date"].required = False
        self.fields["event_location"].required = False
        self.fields["event_end_date"].required = False

        # Add help text for featured checkbox
        self.fields["is_featured"].help_text = (
            "Marque para destacar esta notícia na página inicial"
        )

    def clean(self):
        cleaned_data = super().clean()
        category = cleaned_data.get("category")
        event_date = cleaned_data.get("event_date")
        event_end_date = cleaned_data.get("event_end_date")
        event_location = cleaned_data.get("event_location")

        # Validate event-specific fields if category is Event
        if category and category.name == NewsCategory.EVENT:
            if not event_date:
                self.add_error(
                    "event_date", "Data do evento é obrigatória para eventos."
                )
            if not event_location:
                self.add_error(
                    "event_location", "Local do evento é obrigatório para eventos."
                )

        # Event end date must not be before its start date
        if event_date and event_end_date and event_end_date < event_date:
            self.add_error(
                "event_end_date",
                "A data final do evento não pode ser anterior à data de início.",
            )

        # Validate excerpt length
        excerpt = cleaned_data.get("excerpt")
        if excerpt and len(excerpt) > 300:
            self.add_error("excerpt", "O resumo não pode ter mais de 300 caracteres.")

        return cleaned_data
