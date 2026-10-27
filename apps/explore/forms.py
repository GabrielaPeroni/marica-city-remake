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
        categories = self.fields["categories"]
        categories.queryset = Category.objects.filter(is_active=True).order_by(
            "display_order"
        )
        categories.required = True  # no modelo é opcional (blank=True)


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


PlaceImageFormSet = inlineformset_factory(
    Place,
    PlaceImage,
    form=PlaceImageForm,
    extra=3,
    can_delete=True,
    max_num=10,
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
