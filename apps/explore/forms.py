from django import forms
from django.forms import inlineformset_factory
from django.utils.translation import gettext_lazy as _l

from .models import Category, Place, PlaceImage, PlaceReview


class PlaceForm(forms.ModelForm):
    class Meta:
        model = Place
        fields = [
            "name",
            "description",
            "address",
            "latitude",
            "longitude",
            "categories",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": _l("Nome do lugar"),
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": _l("Descreva o lugar em detalhes..."),
                    "rows": 6,
                }
            ),
            "address": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": _l("Comece a digitar o endereço..."),
                    "rows": 3,
                }
            ),
            "latitude": forms.HiddenInput(),
            "longitude": forms.HiddenInput(),
            "categories": forms.CheckboxSelectMultiple(
                attrs={"class": "form-check-input"}
            ),
        }
        help_texts = {
            "categories": "Selecione uma ou mais categorias que descrevem seu lugar",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Mostrar apenas categorias ativas
        self.fields["categories"].queryset = Category.objects.filter(
            is_active=True
        ).order_by("display_order")

        # Tornar todos os campos obrigatórios
        self.fields["name"].required = True
        self.fields["description"].required = True
        self.fields["address"].required = True
        self.fields["categories"].required = True


class PlaceImageForm(forms.ModelForm):
    class Meta:
        model = PlaceImage
        fields = ["image", "caption", "is_primary", "display_order"]
        widgets = {
            "image": forms.FileInput(
                attrs={
                    "class": "form-control",
                    "accept": "image/*",
                }
            ),
            "caption": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": _l("Descrição da imagem (opcional)"),
                }
            ),
            "is_primary": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "display_order": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                    "value": "0",
                }
            ),
        }
        help_texts = {
            "caption": "Opcional - descrição ou legenda da imagem",
            "is_primary": "Marque se esta é a imagem principal do lugar",
            "display_order": "Ordem de exibição (números menores aparecem primeiro)",
        }


# Criar um formset para lidar com múltiplas imagens
PlaceImageFormSet = inlineformset_factory(
    Place,
    PlaceImage,
    form=PlaceImageForm,
    fields=["image", "caption", "is_primary", "display_order"],
    extra=3,  # Mostrar 3 formulários vazios por padrão
    can_delete=True,
    max_num=10,  # Máximo de 10 imagens por lugar
    validate_max=True,
)


class PlaceReviewForm(forms.ModelForm):
    """Formulário para enviar avaliações de lugares"""

    class Meta:
        model = PlaceReview
        fields = ["rating", "comment"]
        widgets = {
            "rating": forms.RadioSelect(
                choices=[(1, "★"), (2, "★★"), (3, "★★★"), (4, "★★★★"), (5, "★★★★★")],
                attrs={"class": "star-rating-input"},
            ),
            "comment": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": _l("Compartilhe sua experiência neste lugar..."),
                    "rows": 4,
                    "maxlength": "1000",
                }
            ),
        }
        labels = {
            "rating": "Avaliação",
            "comment": "Comentário",
        }
        help_texts = {
            "rating": "Selecione de 1 a 5 estrelas",
            "comment": "Descreva sua experiência (máximo 1000 caracteres)",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["rating"].required = True
        self.fields["comment"].required = True
