from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import UserCreationForm
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

    def clean_email(self):
        # O e-mail identifica a conta na redefinição de senha
        email = self.cleaned_data["email"]
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(_l("Já existe uma conta com este e-mail."))
        return email


class EmailCodeForm(forms.Form):
    code = forms.RegexField(
        regex=r"^\s*\d{6}\s*$",
        label=_l("Código de 6 dígitos"),
        error_messages={"invalid": _l("Digite os 6 dígitos do código.")},
        widget=forms.TextInput(
            attrs={
                "class": "form-control form-control-lg text-center",
                "inputmode": "numeric",
                "autocomplete": "one-time-code",
                "maxlength": "6",
            }
        ),
    )


class PasswordResetRequestForm(forms.Form):
    email = forms.EmailField(
        label=_l("Endereço de e-mail"),
        widget=forms.EmailInput(
            attrs={"class": "form-control", "autocomplete": "email"}
        ),
    )


class PasswordResetConfirmForm(EmailCodeForm):
    new_password1 = forms.CharField(
        label=_l("Nova senha"),
        strip=False,
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "autocomplete": "new-password"}
        ),
    )
    new_password2 = forms.CharField(
        label=_l("Confirmar nova senha"),
        strip=False,
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "autocomplete": "new-password"}
        ),
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        password1 = cleaned.get("new_password1")
        password2 = cleaned.get("new_password2")
        if password1 and password2:
            if password1 != password2:
                self.add_error("new_password2", _l("As senhas não coincidem."))
            else:
                try:
                    password_validation.validate_password(password2, self.user)
                except forms.ValidationError as error:
                    self.add_error("new_password2", error)
        return cleaned
