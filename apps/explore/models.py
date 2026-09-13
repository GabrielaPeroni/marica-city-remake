from django.conf import settings
from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True, help_text="Nome da categoria")

    slug = models.SlugField(
        max_length=100, unique=True, help_text="Identificador amigável para URL"
    )

    description = models.TextField(blank=True, help_text="Descrição da categoria")

    icon = models.CharField(
        max_length=50, blank=True, help_text="Classe do ícone ou emoji para a categoria"
    )

    is_active = models.BooleanField(
        default=True, help_text="Se a categoria está atualmente ativa"
    )

    display_order = models.IntegerField(
        default=0,
        help_text="Ordem em que a categoria aparece (números menores primeiro)",
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["display_order", "name"]
        verbose_name = "Categoria"
        verbose_name_plural = "Categorias"
        indexes = [
            models.Index(fields=["is_active", "display_order"]),
            models.Index(fields=["slug"]),
        ]

    def __str__(self):
        return self.name

    @property
    def active_places_count(self):
        """Contagem de lugares ativos aprovados nesta categoria"""
        return self.places.filter(is_active=True, is_approved=True).count()


class Place(models.Model):
    name = models.CharField(max_length=200, help_text="Nome do lugar")

    description = models.TextField(help_text="Descrição detalhada do lugar")

    address = models.TextField(help_text="Endereço completo do lugar")

    # Coordenadas de localização
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="Coordenada de latitude",
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="Coordenada de longitude",
    )

    # Relacionamentos
    categories = models.ManyToManyField(
        Category,
        related_name="places",
        blank=True,
        help_text="Categorias às quais este lugar pertence",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="places",
        help_text="Usuário que criou este lugar",
    )

    # Campos de status
    is_approved = models.BooleanField(
        default=False, help_text="Se o lugar foi aprovado pelo administrador"
    )

    is_active = models.BooleanField(
        default=True, help_text="Se o lugar está atualmente ativo"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Lugar"
        verbose_name_plural = "Lugares"
        indexes = [
            models.Index(fields=["is_approved", "is_active"]),
            models.Index(fields=["-created_at"]),
        ]

    def __str__(self):
        return self.name

    @property
    def is_pending(self):
        return not self.is_approved

    @property
    def primary_image(self):
        # Iterate the (possibly prefetched) `images` cache instead of
        # filter().first(), which always issues a fresh query and defeats
        # prefetch_related in place-list views.
        for image in self.images.all():
            if image.is_primary:
                return image
        return None

    @property
    def gallery_images(self):
        return self.images.all()

    @property
    def average_rating(self):
        """Calcula a avaliação média de todas as avaliações"""
        from django.db.models import Avg

        result = self.reviews.aggregate(Avg("rating"))
        return round(result["rating__avg"], 1) if result["rating__avg"] else None

    @property
    def review_count(self):
        """Contagem de avaliações para este lugar"""
        return self.reviews.count()


class PlaceImage(models.Model):
    """Imagens para lugares"""

    place = models.ForeignKey(
        Place,
        on_delete=models.CASCADE,
        related_name="images",
        help_text="Lugar ao qual esta imagem pertence",
    )

    image = models.ImageField(
        upload_to="places/images/%Y/%m/", help_text="Imagem do lugar"
    )

    caption = models.CharField(
        max_length=200, blank=True, help_text="Legenda ou descrição da imagem"
    )

    is_primary = models.BooleanField(
        default=False, help_text="Se esta é a imagem principal/primária do lugar"
    )

    display_order = models.IntegerField(
        default=0,
        help_text="Ordem em que a imagem aparece na galeria (números menores primeiro)",
    )

    uploaded_at = models.DateTimeField(
        auto_now_add=True, help_text="Quando a imagem foi carregada"
    )

    class Meta:
        ordering = ["display_order", "-uploaded_at"]
        verbose_name = "Imagem do Lugar"
        verbose_name_plural = "Imagens do Lugar"
        indexes = [
            models.Index(fields=["place", "display_order"]),
            models.Index(fields=["place", "is_primary"]),
        ]

    def __str__(self):
        return f"{self.place.name} - Image {self.id}"

    def save(self, *args, **kwargs):
        if self.is_primary:
            # Define todas as outras imagens deste lugar como não-primárias
            PlaceImage.objects.filter(place=self.place, is_primary=True).update(
                is_primary=False
            )
        super().save(*args, **kwargs)


class PlaceApproval(models.Model):
    class ActionType(models.TextChoices):
        APPROVE = "APPROVE", "Aprovado"
        REJECT = "REJECT", "Rejeitado"
        REQUEST_CHANGES = "REQUEST_CHANGES", "Solicitar Alterações"

    class Meta:
        ordering = ["-reviewed_at"]
        verbose_name = "Aprovação de Lugar"
        verbose_name_plural = "Aprovações de Lugares"
        indexes = [
            models.Index(fields=["place", "-reviewed_at"]),
            models.Index(fields=["reviewer", "-reviewed_at"]),
            models.Index(fields=["action"]),
        ]

    def __str__(self):
        return f"{self.place.name} - {self.get_action_display()} by {self.reviewer}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if self.action == self.ActionType.APPROVE:
            self.place.is_approved = True
            self.place.save(update_fields=["is_approved", "updated_at"])
        elif self.action == self.ActionType.REJECT:
            self.place.is_approved = False
            self.place.is_active = False
            self.place.save(update_fields=["is_approved", "is_active", "updated_at"])

    place = models.ForeignKey(
        Place,
        on_delete=models.CASCADE,
        related_name="approval_history",
        help_text="Lugar sendo revisado",
    )

    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="place_reviews",
        help_text="Usuário administrador que revisou o lugar",
    )

    action = models.CharField(
        max_length=20,
        choices=ActionType.choices,
        help_text="Ação realizada pelo revisor",
    )

    comments = models.TextField(
        blank=True, help_text="Comentários ou feedback do revisor"
    )

    reviewed_at = models.DateTimeField(
        auto_now_add=True, help_text="Quando a revisão foi realizada"
    )


class PlaceReview(models.Model):
    """Avaliações e classificações de usuários para lugares"""

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Avaliação de Lugar"
        verbose_name_plural = "Avaliações de Lugares"
        unique_together = (
            "user",
            "place",
        )  # Usuário pode avaliar um lugar apenas uma vez
        indexes = [
            models.Index(fields=["place", "-created_at"]),
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["rating"]),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.place.name} ({self.rating}★)"

    place = models.ForeignKey(
        Place,
        on_delete=models.CASCADE,
        related_name="reviews",
        help_text="Lugar sendo avaliado",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="place_reviews_written",
        help_text="Usuário que escreveu a avaliação",
    )

    rating = models.IntegerField(
        choices=[
            (1, "1 Estrela"),
            (2, "2 Estrelas"),
            (3, "3 Estrelas"),
            (4, "4 Estrelas"),
            (5, "5 Estrelas"),
        ],
        help_text="Avaliação de 1 a 5 estrelas",
    )

    comment = models.TextField(
        help_text="Comentário/feedback da avaliação",
        max_length=1000,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Favorite(models.Model):
    """
    Modelo para rastrear favoritos do usuário (lugares salvos).
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="favorites",
        help_text="Usuário que favoritou o lugar",
    )

    place = models.ForeignKey(
        Place,
        on_delete=models.CASCADE,
        related_name="favorited_by",
        help_text="Lugar que foi favoritado",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = (
            "user",
            "place",
        )  # Usuário pode favoritar um lugar apenas uma vez
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["place"]),
        ]

    def __str__(self):
        return f"{self.user.username} favorited {self.place.name}"
