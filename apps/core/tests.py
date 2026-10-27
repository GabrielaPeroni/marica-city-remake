from django.contrib.messages import get_messages
from django.test import Client, TestCase, override_settings
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

    @override_settings(GOOGLE_MAPS_API_KEY="test-key")
    def test_landing_page_shows_google_maps_section(self):
        """Testa que a pagina inicial tem o google-maps"""
        response = self.client.get(self.url)
        self.assertContains(response, "landing-map")
        self.assertContains(response, "Navegue pelos Lugares")

    @override_settings(GOOGLE_MAPS_API_KEY="")
    def test_landing_page_hides_map_without_api_key(self):
        """Sem chave, o mapa quebrado do Google não deve ser renderizado"""
        response = self.client.get(self.url)
        self.assertNotContains(response, "landing-map")
        self.assertNotContains(response, "maps.googleapis.com")


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

        self.assertContains(response, "Visão geral")


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


class ErrorPageTests(TestCase):
    """Unknown URLs render the branded 404 page"""

    @override_settings(DEBUG=False)
    def test_unknown_url_uses_branded_404(self):
        response = self.client.get("/pagina-que-nao-existe/")
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "Página não encontrada", status_code=404)
        self.assertContains(response, reverse("explore:explore"), status_code=404)


class LandingLoginPromptTests(TestCase):
    """Anonymous visitors bounced from a protected page are told why"""

    def test_next_param_shows_login_prompt(self):
        response = self.client.get(
            reverse("core:landing"), {"next": "/explore/place/create/"}
        )
        self.assertContains(response, "crie uma conta gratuita")

    def test_no_prompt_without_next(self):
        response = self.client.get(reverse("core:landing"))
        self.assertNotContains(response, "crie uma conta gratuita")


class LanguageSwitcherTests(TestCase):
    """Interface in pt-br by default, switchable to English and Spanish"""

    def test_switcher_is_on_every_page(self):
        for url in (reverse("core:landing"), reverse("news:news_list")):
            response = self.client.get(url)
            self.assertContains(response, 'class="lang-switcher"')
            self.assertContains(response, 'value="es"')

    def test_default_language_is_portuguese(self):
        response = self.client.get(reverse("core:landing"))
        self.assertContains(response, '<html lang="pt-br">')
        self.assertContains(response, "Explorar")

    def test_switching_to_english_translates_the_interface(self):
        self.client.post(
            reverse("set_language"), {"language": "en", "next": "/"}, follow=True
        )
        response = self.client.get(reverse("news:news_list"))
        self.assertContains(response, '<html lang="en">')
        self.assertContains(response, "Upcoming events")
        self.assertNotContains(response, "Próximos eventos")

    def test_switching_to_spanish(self):
        self.client.post(reverse("set_language"), {"language": "es", "next": "/"})
        response = self.client.get(reverse("news:news_list"))
        self.assertContains(response, '<html lang="es">')
        self.assertContains(response, "Próximos eventos")  # mesma grafia em espanhol
        self.assertContains(response, "Explorar lugares")

    def test_javascript_catalog_is_served(self):
        self.client.post(reverse("set_language"), {"language": "en", "next": "/"})
        response = self.client.get(reverse("javascript-catalog"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Remove from favorites")


class ContentTranslationTests(TestCase):
    """Conteúdo traduzido por LLM aparece no idioma escolhido, com fallback"""

    def setUp(self):
        from apps.core.content_translation import translate_object

        self.translate_object = translate_object
        self.category = Category.objects.create(
            name="Praias", slug="praias", description="As melhores praias"
        )

    def _fake(self, prompt):
        lang = "es" if "Spanish" in prompt else "en"
        return {
            "en": {"name": "Beaches", "description": "The best beaches"},
            "es": {"name": "Playas", "description": "Las mejores playas"},
        }[lang]

    def test_translations_are_stored_per_language(self):
        data = self.translate_object(self.category, ask=self._fake)
        self.category.refresh_from_db()
        self.assertEqual(self.category.translations["en"]["name"], "Beaches")
        self.assertEqual(data["es"]["description"], "Las mejores playas")

    def test_pages_show_translation_and_fall_back_to_portuguese(self):
        self.translate_object(self.category, ask=self._fake)
        response = self.client.get(reverse("core:landing"))
        self.assertContains(response, "Praias")
        self.client.post(reverse("set_language"), {"language": "en", "next": "/"})
        response = self.client.get(reverse("core:landing"))
        self.assertContains(response, "Beaches")
        Category.objects.create(name="Lagoas", slug="lagoas")
        self.assertContains(self.client.get(reverse("core:landing")), "Lagoas")

    def test_editing_the_source_marks_translation_stale(self):
        from apps.core.content_translation import needs_translation

        self.translate_object(self.category, ask=self._fake)
        self.category.refresh_from_db()
        self.assertFalse(needs_translation(self.category))
        self.category.description = "Outra descrição"
        self.assertTrue(needs_translation(self.category))

    def test_command_stops_quietly_without_ollama(self):
        from io import StringIO
        from unittest import mock
        from urllib.error import URLError

        from django.core.management import call_command

        err = StringIO()
        with mock.patch(
            "apps.core.content_translation._ollama",
            autospec=True,
            side_effect=URLError("down"),
        ):
            call_command("translate_content", stdout=StringIO(), stderr=err)
        self.assertIn("Ollama", err.getvalue())


class AdminNewsFilterTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="editor", password="pass123", is_staff=True
        )
        category, _ = NewsCategory.objects.get_or_create(name=NewsCategory.NEWS)
        for title, status in (("Pub", News.PUBLISHED), ("Rasc", News.DRAFT)):
            News.objects.create(
                title=title,
                content="c",
                category=category,
                author=self.staff,
                status=status,
            )
        self.client.login(username="editor", password="pass123")

    def test_status_tabs_filter_the_list(self):
        url = reverse("core:admin_news_list")
        published = self.client.get(url + "?status=published").context["news_list"]
        drafts = self.client.get(url + "?status=draft").context["news_list"]
        self.assertEqual([n.title for n in published], ["Pub"])
        self.assertEqual([n.title for n in drafts], ["Rasc"])


class VisitPageTests(TestCase):
    def test_visit_info_lives_on_the_about_page(self):
        landing = self.client.get(reverse("core:landing"))
        self.assertContains(landing, reverse("core:about") + "#visite")
        self.assertRedirects(
            self.client.get("/planeje-sua-visita/"),
            "/sobre/#visite",
            status_code=301,
            fetch_redirect_response=False,
        )
        response = self.client.get(reverse("core:about"))
        self.assertContains(response, "Vermelhinhos")
        self.assertContains(response, "<strong>192</strong>", html=False)


class AdminNewsBulkTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="staffuser", password="testpass123", is_staff=True
        )
        self.regular = User.objects.create_user(
            username="regularuser", password="testpass123"
        )
        category, _ = NewsCategory.objects.get_or_create(name=NewsCategory.EVENT)
        self.items = [
            News.objects.create(
                title=f"Item {i}",
                content="Content",
                author=self.staff,
                category=category,
                status=News.DRAFT,
            )
            for i in range(3)
        ]
        self.url = reverse("core:admin_news_bulk")

    def _post(self, ids, action):
        return self.client.post(self.url, {"ids": ids, "action": action})

    def test_bulk_publish(self):
        self.client.login(username="staffuser", password="testpass123")
        self._post([i.pk for i in self.items[:2]], "publish")
        statuses = [News.objects.get(pk=i.pk).status for i in self.items]
        self.assertEqual(statuses, [News.PUBLISHED, News.PUBLISHED, News.DRAFT])
        self.assertIsNotNone(News.objects.get(pk=self.items[0].pk).publish_date)

    def test_bulk_archive(self):
        self.client.login(username="staffuser", password="testpass123")
        self._post([i.pk for i in self.items], "archive")
        self.assertEqual(News.objects.filter(status=News.ARCHIVED).count(), 3)

    def test_bulk_delete(self):
        self.client.login(username="staffuser", password="testpass123")
        self._post([self.items[0].pk, self.items[1].pk], "delete")
        self.assertEqual(News.objects.count(), 1)

    def test_already_archived_ignored_in_count(self):
        self.client.login(username="staffuser", password="testpass123")
        self.items[0].status = News.ARCHIVED
        self.items[0].save()
        response = self._post([self.items[0].pk, self.items[1].pk], "archive")
        messages = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertIn("1 evento arquivado", messages)

    def test_non_staff_forbidden(self):
        self.client.login(username="regularuser", password="testpass123")
        self._post([self.items[0].pk], "delete")
        self.assertEqual(News.objects.count(), 3)

    def test_invalid_action_changes_nothing(self):
        self.client.login(username="staffuser", password="testpass123")
        self._post([self.items[0].pk], "explode")
        self.assertEqual(News.objects.filter(status=News.DRAFT).count(), 3)

    def test_list_page_has_checkboxes(self):
        self.client.login(username="staffuser", password="testpass123")
        response = self.client.get(reverse("core:admin_news_list"))
        self.assertContains(response, "data-bulk-item", count=3)
