from django.test import Client, TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.core.views import calculate_percentage_change
from apps.explore.models import Category, Place
from apps.news.models import News, NewsCategory


class LandingPageTests(TestCase):
    """Teste suite pra funcionalidade da pagina inicial"""

    def setUp(self):
        """Prepara a data"""
        self.client = Client()
        self.url = reverse("core:landing")

        # Cria as categorias de teste
        self.category1 = Category.objects.create(
            name="Restaurantes", slug="restaurantes", icon="🍽️"
        )
        self.category2 = Category.objects.create(
            name="Natureza", slug="natureza", icon="🌳"
        )

    def test_landing_page_loads(self):
        """Testa que a pagina inicial carrega"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/landing.html")

    def test_landing_page_shows_categories(self):
        """Testa que a pagina inicial mostra categorias"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Restaurantes")
        self.assertContains(response, "Natureza")
        self.assertContains(response, "🍽️")
        self.assertContains(response, "🌳")

    def test_landing_page_shows_title(self):
        """Testa que a pagina inicial mostra o titulo correto"""
        response = self.client.get(self.url)
        self.assertContains(response, "MaricaCity")
        self.assertContains(response, "Descubra")

    def test_landing_page_has_cta_buttons(self):
        """Test that landing page has call-to-action buttons"""
        response = self.client.get(self.url)
        self.assertContains(response, "Explorar")
        self.assertContains(response, "Cadastre-se")

    def test_landing_page_shows_hero_section(self):
        """Testa que a pagina inicial tem o carrosel"""
        response = self.client.get(self.url)
        self.assertContains(response, "hero-section")
        self.assertContains(response, "swiper")

    def test_landing_page_shows_google_maps_section(self):
        """Testa que a pagina inicial tem o google-maps"""
        response = self.client.get(self.url)
        self.assertContains(response, "landing-map")
        self.assertContains(response, "Navegue pelos Lugares")


class AboutPageTests(TestCase):
    """Teste suite pra funcionalidade da pagina Sobre"""

    def setUp(self):
        """Prepara a data"""
        self.client = Client()
        self.url = reverse("core:about")

    def test_about_page_loads(self):
        """Testa que a pagina Sobre carrega"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/about.html")

    def test_about_page_contains_info(self):
        """Testa que a pagina Sobre contem informacoes"""
        response = self.client.get(self.url)
        self.assertContains(response, "Sobre")


class AdminDashboardTests(TestCase):
    """Teste suite pra funcionalidade do admin dashboard"""

    def setUp(self):
        """Prepara a data"""
        self.client = Client()
        self.url = reverse("core:admin_dashboard")

        self.staff_user = User.objects.create_user(
            username="staffuser", password="testpass123", is_staff=True
        )
        self.regular_user = User.objects.create_user(
            username="regularuser", password="testpass123", is_staff=False
        )

        self.category = Category.objects.create(
            name="Restaurantes", slug="restaurantes", icon="🍽️"
        )

        self.approved_place = Place.objects.create(
            name="Approved Place",
            description="An approved place",
            address="123 Test St",
            created_by=self.regular_user,
            is_approved=True,
        )

        self.pending_place = Place.objects.create(
            name="Pending Place",
            description="A pending place",
            address="456 Test Ave",
            created_by=self.regular_user,
            is_approved=False,
        )

    def test_admin_dashboard_requires_login(self):
        """Testa que o admin dash requer autenticacao"""
        response = self.client.get(self.url)
        self.assertRedirects(response, f"/?next={self.url}")

    def test_admin_dashboard_requires_staff_permission(self):
        """Testa que o admin dash requer permissao de staff (is_staff=True)"""
        # Try with regular user - should be denied access
        self.client.login(username="regularuser", password="testpass123")
        response = self.client.get(self.url)
        # Should either return 403 or redirect (both are valid)
        self.assertIn(response.status_code, [302, 403])

    def test_admin_dashboard_loads_for_staff(self):
        """Testa que o admin dash carrega para staff"""
        self.client.login(username="staffuser", password="testpass123")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/admin_dashboard.html")

    def test_admin_dashboard_shows_statistics(self):
        """Testa que o that admin dash mostra statisticas"""
        self.client.login(username="staffuser", password="testpass123")
        response = self.client.get(self.url)

        self.assertIn("total_places", response.context)
        self.assertIn("pending_places", response.context)
        self.assertIn("approved_places", response.context)
        self.assertIn("total_users", response.context)

        self.assertEqual(response.context["total_places"], 2)
        self.assertEqual(response.context["pending_places"], 1)
        self.assertEqual(response.context["approved_places"], 1)
        self.assertEqual(response.context["total_users"], 2)

    def test_admin_dashboard_shows_content(self):
        """Testa que o that admin dash mostra conteudo relevante"""
        self.client.login(username="staffuser", password="testpass123")
        response = self.client.get(self.url)

        self.assertContains(response, "DASHBOARD")


class HealthViewTests(TestCase):
    """Testa a probe de liveness/readiness"""

    def setUp(self):
        self.client = Client()
        self.url = reverse("healthz")

    def test_health_endpoint_returns_ok(self):
        """Testa que o endpoint de health retorna status ok"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_health_endpoint_rejects_post(self):
        """Testa que o endpoint de health só aceita GET"""
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 405)


class CalculatePercentageChangeTests(TestCase):
    """Testes unitários para a função utilitária calculate_percentage_change"""

    def test_increase_from_positive_previous(self):
        """Testa cálculo normal de aumento percentual"""
        self.assertEqual(calculate_percentage_change(15, 10), 50.0)

    def test_decrease_from_positive_previous(self):
        """Testa cálculo normal de diminuição percentual"""
        self.assertEqual(calculate_percentage_change(5, 10), -50.0)

    def test_zero_previous_with_positive_current_returns_100(self):
        """Testa que ir de 0 para um valor positivo retorna 100%"""
        self.assertEqual(calculate_percentage_change(5, 0), 100)

    def test_zero_previous_with_zero_current_returns_zero(self):
        """Testa que 0 para 0 não é tratado como aumento"""
        self.assertEqual(calculate_percentage_change(0, 0), 0)


class AdminNewsListViewTests(TestCase):
    """Testes para a listagem administrativa de notícias"""

    def setUp(self):
        self.client = Client()
        self.staff_user = User.objects.create_user(
            username="staffuser", password="testpass123", is_staff=True
        )
        self.regular_user = User.objects.create_user(
            username="regularuser", password="testpass123", is_staff=False
        )
        self.category, _ = NewsCategory.objects.get_or_create(name=NewsCategory.NEWS)
        self.published = News.objects.create(
            title="Published Item",
            content="Content",
            author=self.staff_user,
            category=self.category,
            status=News.PUBLISHED,
        )
        self.draft = News.objects.create(
            title="Draft Item",
            content="Content",
            author=self.staff_user,
            category=self.category,
            status=News.DRAFT,
        )
        self.url = reverse("core:admin_news_list")

    def test_requires_moderator_permission(self):
        """Testa que apenas moderadores podem ver a lista"""
        self.client.login(username="regularuser", password="testpass123")
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse("core:landing"))

    def test_loads_with_counts(self):
        """Testa que a página carrega com contagens corretas"""
        self.client.login(username="staffuser", password="testpass123")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_count"], 2)
        self.assertEqual(response.context["published_count"], 1)
        self.assertEqual(response.context["draft_count"], 1)

    def test_filter_by_status(self):
        """Testa filtro por status de publicação"""
        self.client.login(username="staffuser", password="testpass123")
        response = self.client.get(self.url + "?status=" + News.PUBLISHED)
        titles = {n.title for n in response.context["news_list"]}
        self.assertEqual(titles, {"Published Item"})

    def test_filter_by_search_query(self):
        """Testa filtro por busca no título"""
        self.client.login(username="staffuser", password="testpass123")
        response = self.client.get(self.url + "?q=Draft")
        titles = {n.title for n in response.context["news_list"]}
        self.assertEqual(titles, {"Draft Item"})


class AdminNewsCreateViewTests(TestCase):
    """Testes para a criação de notícias pelo admin"""

    def setUp(self):
        self.client = Client()
        self.staff_user = User.objects.create_user(
            username="staffuser", password="testpass123", is_staff=True
        )
        self.regular_user = User.objects.create_user(
            username="regularuser", password="testpass123", is_staff=False
        )
        self.category, _ = NewsCategory.objects.get_or_create(name=NewsCategory.NEWS)
        self.url = reverse("core:admin_news_create")

    def test_requires_moderator_permission(self):
        """Testa que apenas moderadores podem acessar a criação"""
        self.client.login(username="regularuser", password="testpass123")
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse("core:landing"))

    def test_get_shows_form(self):
        """Testa que GET exibe o formulário de criação"""
        self.client.login(username="staffuser", password="testpass123")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/admin/news_form.html")

    def test_valid_post_creates_news(self):
        """Testa que POST válido cria a notícia com o autor correto"""
        self.client.login(username="staffuser", password="testpass123")
        response = self.client.post(
            self.url,
            data={
                "title": "Brand New Article",
                "category": self.category.pk,
                "content": "Some content",
                "excerpt": "",
                "status": News.DRAFT,
            },
        )
        self.assertRedirects(response, reverse("core:admin_news_list"))
        news = News.objects.get(title="Brand New Article")
        self.assertEqual(news.author, self.staff_user)

    def test_invalid_post_shows_errors(self):
        """Testa que POST inválido não cria a notícia e reexibe o formulário"""
        self.client.login(username="staffuser", password="testpass123")
        response = self.client.post(self.url, data={"title": ""})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(News.objects.count(), 0)


class AdminNewsEditViewTests(TestCase):
    """Testes para a edição de notícias pelo admin"""

    def setUp(self):
        self.client = Client()
        self.staff_user = User.objects.create_user(
            username="staffuser", password="testpass123", is_staff=True
        )
        self.regular_user = User.objects.create_user(
            username="regularuser", password="testpass123", is_staff=False
        )
        self.category, _ = NewsCategory.objects.get_or_create(name=NewsCategory.NEWS)
        self.news = News.objects.create(
            title="Original Title",
            content="Original content",
            author=self.staff_user,
            category=self.category,
            status=News.DRAFT,
        )
        self.url = reverse("core:admin_news_edit", kwargs={"pk": self.news.pk})

    def test_requires_moderator_permission(self):
        """Testa que apenas moderadores podem editar"""
        self.client.login(username="regularuser", password="testpass123")
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse("core:landing"))

    def test_get_shows_prefilled_form(self):
        """Testa que GET exibe o formulário preenchido"""
        self.client.login(username="staffuser", password="testpass123")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Original Title")

    def test_valid_post_updates_news(self):
        """Testa que POST válido atualiza a notícia"""
        self.client.login(username="staffuser", password="testpass123")
        response = self.client.post(
            self.url,
            data={
                "title": "Updated Title",
                "category": self.category.pk,
                "content": "Updated content",
                "excerpt": "",
                "status": News.DRAFT,
            },
        )
        self.assertRedirects(response, reverse("core:admin_news_list"))
        self.news.refresh_from_db()
        self.assertEqual(self.news.title, "Updated Title")

    def test_nonexistent_news_returns_404(self):
        """Testa que editar notícia inexistente retorna 404"""
        self.client.login(username="staffuser", password="testpass123")
        response = self.client.get(
            reverse("core:admin_news_edit", kwargs={"pk": 999999})
        )
        self.assertEqual(response.status_code, 404)


class AdminNewsDeleteViewTests(TestCase):
    """Testes para a exclusão de notícias pelo admin"""

    def setUp(self):
        self.client = Client()
        self.staff_user = User.objects.create_user(
            username="staffuser", password="testpass123", is_staff=True
        )
        self.regular_user = User.objects.create_user(
            username="regularuser", password="testpass123", is_staff=False
        )
        self.category, _ = NewsCategory.objects.get_or_create(name=NewsCategory.NEWS)
        self.news = News.objects.create(
            title="To Be Deleted",
            content="Content",
            author=self.staff_user,
            category=self.category,
        )
        self.url = reverse("core:admin_news_delete", kwargs={"pk": self.news.pk})

    def test_requires_moderator_permission(self):
        """Testa que apenas moderadores podem excluir"""
        self.client.login(username="regularuser", password="testpass123")
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse("core:landing"))
        self.assertTrue(News.objects.filter(pk=self.news.pk).exists())

    def test_get_shows_confirmation(self):
        """Testa que GET exibe a página de confirmação"""
        self.client.login(username="staffuser", password="testpass123")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/admin/news_delete_confirm.html")

    def test_post_deletes_news(self):
        """Testa que POST exclui a notícia"""
        self.client.login(username="staffuser", password="testpass123")
        response = self.client.post(self.url)
        self.assertRedirects(response, reverse("core:admin_news_list"))
        self.assertFalse(News.objects.filter(pk=self.news.pk).exists())
