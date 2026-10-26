from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class NewsCategory(models.Model):
    """Categorias para notícias e eventos"""

    NEWS = "Noticias"
    EVENT = "Evento"
    ANNOUNCEMENT = "Anuncios"

    CATEGORY_CHOICES = [
        (NEWS, "Noticias"),
        (EVENT, "Eventos"),
        (ANNOUNCEMENT, "Anuncios"),
    ]

    name = models.CharField(max_length=50, choices=CATEGORY_CHOICES, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(
        max_length=50, blank=True, help_text="Classe de ícone ou emoji"
    )

    class Meta:
        verbose_name = "News Category"
        verbose_name_plural = "News Categories"
        ordering = ["name"]

    def __str__(self):
        return self.get_name_display()

    @property
    def kind(self):
        """Chave estável usada pelas classes CSS (kind-news, kind-event...)"""
        return {self.EVENT: "event", self.ANNOUNCEMENT: "announcement"}.get(
            self.name, "news"
        )

    @property
    def label(self):
        return {"event": "Eventos", "announcement": "Anúncios"}.get(
            self.kind, "Notícias"
        )

    @property
    def icon_class(self):
        return {
            "event": "bi-calendar-event",
            "announcement": "bi-megaphone",
        }.get(self.kind, "bi-newspaper")


class NewsQuerySet(models.QuerySet):
    def published(self):
        return self.filter(status=News.PUBLISHED, publish_date__lte=timezone.now())

    def upcoming_events(self):
        """Eventos que ainda não terminaram, do mais próximo ao mais distante"""
        now = timezone.now()
        return (
            self.filter(category__name=NewsCategory.EVENT)
            .filter(models.Q(event_date__gt=now) | models.Q(event_end_date__gt=now))
            .order_by("event_date")
        )


class News(models.Model):
    """Notícias e eventos para a cidade de Maricá"""

    DRAFT = "Em Progresso"
    PUBLISHED = "Publicado"
    ARCHIVED = "Arquivado"

    STATUS_CHOICES = [
        (DRAFT, "Em Progresso"),
        (PUBLISHED, "Publicado"),
        (ARCHIVED, "Arquivado"),
    ]

    # Campos básicos
    title = models.CharField(max_length=200, help_text="Titulo da noticia ou evento")
    slug = models.SlugField(
        max_length=250, unique=True, blank=True, help_text="URL-friendly identifier"
    )
    content = models.TextField(help_text="Full content of the news or event")
    excerpt = models.TextField(
        max_length=300,
        blank=True,
        help_text="Short summary for listings (max 300 chars)",
    )

    # Categorização
    category = models.ForeignKey(
        NewsCategory,
        on_delete=models.PROTECT,
        related_name="news_items",
        help_text="Type of content (news, event, announcement)",
    )

    # Imagens
    featured_image = models.ImageField(
        upload_to="news/%Y/%m/",
        blank=True,
        null=True,
        help_text="Main image for the news/event",
    )
    image_caption = models.CharField(
        max_length=200, blank=True, help_text="Caption for featured image"
    )

    # Campos específicos de eventos
    event_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date and time of event (for events only)",
    )
    event_location = models.CharField(
        max_length=200,
        blank=True,
        help_text="Location of event (for events only)",
    )
    event_end_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="End date and time of event (optional)",
    )

    # Gerenciamento de publicação
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=DRAFT,
        help_text="Publication status",
    )
    publish_date = models.DateTimeField(
        default=timezone.now,
        help_text="Date when this should be published",
    )

    # Autor e metadados
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="news_items",
        help_text="User who created this news/event",
    )
    is_featured = models.BooleanField(
        default=False,
        help_text="Show in featured/highlighted sections",
    )
    view_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of times this has been viewed",
    )

    # Origem externa (itens importados de outros veículos)
    source_name = models.CharField(
        max_length=120, blank=True, help_text="Veículo que publicou a matéria original"
    )
    source_url = models.URLField(
        max_length=1000, blank=True, help_text="Link para a matéria original"
    )

    # Datas e horários
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = NewsQuerySet.as_manager()

    class Meta:
        ordering = ["-publish_date", "-created_at"]
        verbose_name = "News/Event"
        verbose_name_plural = "News/Events"
        indexes = [
            models.Index(fields=["status", "-publish_date"]),
            models.Index(fields=["category", "status"]),
            models.Index(fields=["slug"]),
            models.Index(fields=["-publish_date"]),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        """Gerar slug automaticamente se não fornecido"""
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while News.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug

        # Gerar resumo automaticamente se não fornecido
        if not self.excerpt and self.content:
            self.excerpt = (
                self.content[:297] + "..." if len(self.content) > 300 else self.content
            )

        # Auto-set publish_date when status changes to PUBLISHED
        if self.status == self.PUBLISHED:
            # Check if this is a new publication (comparing with DB state)
            if self.pk:
                try:
                    old_instance = News.objects.get(pk=self.pk)
                    # If status changed from non-published to published, update date
                    if old_instance.status != self.PUBLISHED:
                        self.publish_date = timezone.now()
                except News.DoesNotExist:
                    # New object being created as published
                    if not self.publish_date or self.publish_date > timezone.now():
                        self.publish_date = timezone.now()
            else:
                # New object, set publish date if not already set or future dated
                if not self.publish_date or self.publish_date > timezone.now():
                    self.publish_date = timezone.now()

        super().save(*args, **kwargs)

    @property
    def is_external(self):
        return bool(self.source_url)

    @property
    def tone(self):
        """Índice de cor estável por veículo, para variar cards sem imagem"""
        return sum(map(ord, self.source_name)) % 5 if self.source_name else 0

    @property
    def is_event(self):
        """Verificar se isto é um evento"""
        return self.category.name == NewsCategory.EVENT

    @property
    def is_upcoming_event(self):
        """Verificar se isto é um evento futuro"""
        if not self.is_event or not self.event_date:
            return False
        return self.event_date > timezone.now()

    @property
    def is_ongoing_event(self):
        if not self.is_event or not self.event_date or not self.event_end_date:
            return False
        return self.event_date <= timezone.now() < self.event_end_date

    @property
    def is_past_event(self):
        """Verificar se isto é um evento passado"""
        if not self.is_event or not self.event_date:
            return False
        return (self.event_end_date or self.event_date) <= timezone.now()

    def increment_view_count(self):
        """Incrementar o contador de visualizações"""
        self.view_count += 1
        self.save(update_fields=["view_count"])
