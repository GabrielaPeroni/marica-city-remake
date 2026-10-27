from urllib.parse import urlencode

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _l


class NewsCategory(models.Model):
    """Categorias para notícias e eventos"""

    NEWS = "Noticias"
    EVENT = "Evento"
    ANNOUNCEMENT = "Anuncios"

    CATEGORY_CHOICES = [
        (NEWS, _l("Noticias")),
        (EVENT, _l("Eventos")),
        (ANNOUNCEMENT, _l("Anuncios")),
    ]

    name = models.CharField(max_length=50, choices=CATEGORY_CHOICES, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(
        max_length=50, blank=True, help_text=_l("Classe de ícone ou emoji")
    )

    class Meta:
        verbose_name = "News Category"
        verbose_name_plural = "News Categories"
        ordering = ["name"]

    def __str__(self):
        return self.get_name_display()


class NewsQuerySet(models.QuerySet):
    def published(self):
        return self.filter(status=News.PUBLISHED, publish_date__lte=timezone.now())

    def events(self):
        return self.filter(category__name=NewsCategory.EVENT)

    def upcoming_events(self):
        """Eventos que ainda não terminaram, do mais próximo ao mais distante"""
        now = timezone.now()
        return (
            self.events()
            .filter(models.Q(event_date__gt=now) | models.Q(event_end_date__gt=now))
            .order_by("event_date")
        )


class News(models.Model):
    """Notícias e eventos para a cidade de Maricá"""

    TRANSLATABLE_FIELDS = ("title", "excerpt", "content")

    DRAFT = "Em Progresso"
    PUBLISHED = "Publicado"
    ARCHIVED = "Arquivado"

    STATUS_CHOICES = [
        (DRAFT, _l("Em Progresso")),
        (PUBLISHED, _l("Publicado")),
        (ARCHIVED, _l("Arquivado")),
    ]

    # Campos básicos
    title = models.CharField(
        max_length=200, help_text=_l("Titulo da noticia ou evento")
    )
    slug = models.SlugField(
        max_length=250, unique=True, blank=True, help_text=_l("URL-friendly identifier")
    )
    content = models.TextField(help_text=_l("Full content of the news or event"))
    excerpt = models.TextField(
        max_length=300,
        blank=True,
        help_text=_l("Short summary for listings (max 300 chars)"),
    )

    # Categorização
    category = models.ForeignKey(
        NewsCategory,
        on_delete=models.PROTECT,
        related_name="news_items",
        help_text=_l("Type of content (news, event, announcement)"),
    )

    # Imagens
    featured_image = models.ImageField(
        upload_to="news/%Y/%m/",
        blank=True,
        null=True,
        help_text=_l("Main image for the news/event"),
    )
    image_caption = models.CharField(
        max_length=200, blank=True, help_text=_l("Caption for featured image")
    )

    # Campos específicos de eventos
    event_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_l("Date and time of event (for events only)"),
    )
    event_location = models.CharField(
        max_length=200,
        blank=True,
        help_text=_l("Location of event (for events only)"),
    )
    event_end_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_l("End date and time of event (optional)"),
    )

    # Gerenciamento de publicação
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=DRAFT,
        help_text=_l("Publication status"),
    )
    publish_date = models.DateTimeField(
        default=timezone.now,
        help_text=_l("Date when this should be published"),
    )

    # Autor e metadados
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="news_items",
        help_text=_l("User who created this news/event"),
    )
    is_featured = models.BooleanField(
        default=False,
        help_text=_l("Show in featured/highlighted sections"),
    )
    view_count = models.PositiveIntegerField(
        default=0,
        help_text=_l("Number of times this has been viewed"),
    )

    # Origem externa (itens importados de outros veículos)
    source_name = models.CharField(
        max_length=120,
        blank=True,
        help_text=_l("Veículo que publicou a matéria original"),
    )
    source_url = models.URLField(
        max_length=1000, blank=True, help_text=_l("Link para a matéria original")
    )

    # Datas e horários
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = NewsQuerySet.as_manager()

    translations = models.JSONField(
        default=dict,
        blank=True,
        help_text=_l("Traduções automáticas (en, es); editáveis pela equipe"),
    )

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
        if not self.slug:
            base = slugify(self.title)
            self.slug, n = base, 1
            while News.objects.filter(slug=self.slug).exists():
                self.slug, n = f"{base}-{n}", n + 1

        if not self.excerpt and self.content:
            self.excerpt = (
                self.content[:297] + "..." if len(self.content) > 300 else self.content
            )

        # Data de publicação = momento em que passa a "Publicado" (ou a data
        # informada, se já passou, quando o item é criado publicado)
        if self.status == self.PUBLISHED:
            now = timezone.now()
            previous = News.objects.filter(pk=self.pk).values_list("status", flat=True)
            if previous:
                if previous[0] != self.PUBLISHED:
                    self.publish_date = now
            elif not self.publish_date or self.publish_date > now:
                self.publish_date = now

        super().save(*args, **kwargs)

    @property
    def is_event(self):
        """Verificar se isto é um evento"""
        return self.category.name == NewsCategory.EVENT

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

    @property
    def maps_url(self):
        if not self.event_location:
            return ""
        return "https://www.google.com/maps/search/?" + urlencode(
            {"api": 1, "query": f"{self.event_location}, Maricá - RJ"}
        )

    def increment_view_count(self):
        """Soma 1 no banco (atômico, sem save()) e no objeto em memória"""
        News.objects.filter(pk=self.pk).update(view_count=models.F("view_count") + 1)
        self.view_count += 1


class EventCandidate(models.Model):
    """Evento encontrado pelo crawler, aguardando triagem antes de virar um News"""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    STATUS_CHOICES = [
        (PENDING, _l("Aguardando triagem")),
        (APPROVED, _l("Publicado")),
        (REJECTED, _l("Descartado")),
    ]

    source = models.CharField(max_length=40)
    source_id = models.CharField(max_length=64)
    source_name = models.CharField(max_length=120)
    source_url = models.URLField(max_length=1000)
    source_published_at = models.DateTimeField()

    title = models.CharField(max_length=200)
    summary = models.TextField()
    image_url = models.URLField(max_length=1000, blank=True)
    event_date = models.DateTimeField(null=True, blank=True)
    event_end_date = models.DateTimeField(null=True, blank=True)
    event_location = models.CharField(max_length=200, blank=True)

    score = models.PositiveSmallIntegerField(default=0)
    signals = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING)
    possible_duplicate = models.ForeignKey(
        "News", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    news = models.OneToOneField(
        "News",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="candidate",
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["event_date", "-score"]
        constraints = [
            models.UniqueConstraint(
                fields=["source", "source_id"], name="unique_candidate_per_source"
            )
        ]

    def __str__(self):
        return self.title
