from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.utils.translation import gettext_lazy as _l

from .models import User


class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": _l("Endereço de e-mail"),
            }
        ),
    )

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")
        widgets = {
            "username": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": _l("Nome de usuário"),
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs["autocomplete"] = "username"
        self.fields["email"].widget.attrs["autocomplete"] = "email"
        self.fields["password1"].widget.attrs.update(
            {
                "class": "form-control",
                "placeholder": _l("Senha"),
            }
        )
        self.fields["password2"].widget.attrs.update(
            {
                "class": "form-control",
                "placeholder": _l("Confirmar senha"),
            }
        )


class UserLoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": _l("Nome de usuário"),
            }
        )
    )

    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": _l("Senha"),
            }
        )
    )
