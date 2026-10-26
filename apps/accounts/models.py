from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _l


class User(AbstractUser):
    @property
    def can_create_places(self):
        """Verifica se o usuário pode criar lugares - todos os usuários autenticados podem criar"""
        return self.is_authenticated

    @property
    def can_moderate(self):
        """Verifica se o usuário pode moderar/aprovar lugares - apenas staff/superusuário"""
        return self.is_staff or self.is_superuser

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Usuário"
        verbose_name_plural = "Usuários"

    def __str__(self):
        return self.username

    bio = models.TextField(blank=True, null=True, help_text=_l("Biografia do usuário"))

    # Informações de contato
    contact_phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text=_l("Número de telefone de contato"),
    )
    contact_email = models.EmailField(
        blank=True,
        null=True,
        help_text=_l("E-mail de contato público (diferente do e-mail de login)"),
    )
    contact_website = models.URLField(
        blank=True, null=True, help_text=_l("Website ou URL de rede social")
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
