from datetime import datetime, timedelta
from datetime import timezone as dt_timezone
from io import StringIO
from pathlib import Path

from django.contrib import admin
from django.core.management import call_command
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.news import event_crawler, importer
from apps.news.forms import NewsForm
from apps.news.models import EventCandidate, News, NewsCategory


class NewsCategoryModelTests(TestCase):
    """Test suite for NewsCategory model"""

    def test_create_news_category(self):
        """Test creating a news category (or getting existing from migration)"""
        category, created = NewsCategory.objects.get_or_create(
            name=NewsCategory.NEWS,
            defaults={"description": "Latest news", "icon": "📰"},
        )
        self.assertEqual(category.name, NewsCategory.NEWS)
        self.assertEqual(str(category), "Noticias")

    def test_category_choices(self):
        """Test that all category choices work"""
        news_cat, _ = NewsCategory.objects.get_or_create(name=NewsCategory.NEWS)
        event_cat, _ = NewsCategory.objects.get_or_create(name=NewsCategory.EVENT)
        announcement_cat, _ = NewsCategory.objects.get_or_create(
            name=NewsCategory.ANNOUNCEMENT
        )

        self.assertEqual(news_cat.get_name_display(), "Noticias")
        self.assertEqual(event_cat.get_name_display(), "Eventos")
        self.assertEqual(announcement_cat.get_name_display(), "Anuncios")


class NewsModelTests(TestCase):
    """Test suite for News model"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username="testauthor", password="testpass123", is_staff=True
        )
        self.category, _ = NewsCategory.objects.get_or_create(
            name=NewsCategory.NEWS, defaults={"description": "Latest news"}
        )

    def test_create_news(self):
        """Test creating a news article"""
        news = News.objects.create(
            title="Test News Article",
            content="This is test content",
            author=self.user,
            category=self.category,
            status=News.PUBLISHED,
        )
        self.assertEqual(news.title, "Test News Article")
        self.assertEqual(news.status, News.PUBLISHED)
        self.assertIsNotNone(news.slug)  # Auto-generated slug
        self.assertIsNotNone(news.publish_date)  # Auto-set on publish

    def test_news_string_representation(self):
        """Test the string representation of news"""
        news = News.objects.create(
            title="Test News",
            content="Content",
            author=self.user,
            category=self.category,
            publish_date=timezone.now(),
        )
        self.assertEqual(str(news), "Test News")

    def test_news_auto_slug_generation(self):
        """Test that slug is auto-generated from title"""
        news = News.objects.create(
            title="Test News Article",
            content="Content",
            author=self.user,
            category=self.category,
            publish_date=timezone.now(),
        )
        self.assertEqual(news.slug, "test-news-article")

    def test_news_defaults_to_draft(self):
        """Test that new news defaults to draft status"""
        news = News.objects.create(
            title="Draft News",
            content="Content",
            author=self.user,
            category=self.category,
            publish_date=timezone.now(),
        )
        self.assertEqual(news.status, News.DRAFT)

    def test_news_is_event_property(self):
        """Test is_event property for event category"""
        event_category, _ = NewsCategory.objects.get_or_create(name=NewsCategory.EVENT)

        news = News.objects.create(
            title="Regular News",
            content="Content",
            author=self.user,
            category=self.category,
            publish_date=timezone.now(),
        )

        event = News.objects.create(
            title="Event News",
            content="Content",
            author=self.user,
            category=event_category,
            publish_date=timezone.now(),
            event_date=timezone.now(),
        )

        self.assertFalse(news.is_event)
        self.assertTrue(event.is_event)

    def test_slug_collision_appends_incrementing_suffix(self):
        """Test creating multiple News with the same title generates unique slugs"""
        first = News.objects.create(
            title="Duplicate Title",
            content="Content",
            author=self.user,
            category=self.category,
        )
        second = News.objects.create(
            title="Duplicate Title",
            content="Content",
            author=self.user,
            category=self.category,
        )
        self.assertEqual(first.slug, "duplicate-title")
        self.assertEqual(second.slug, "duplicate-title-1")

    def test_publish_date_reset_when_pk_set_but_row_missing(self):
        """Regression path: if an object has a pk assigned but no matching
        row exists yet (News.objects.get raises DoesNotExist), publishing
        it should still set publish_date to now rather than crash."""
        news = News(
            pk=999999,
            title="Phantom Pk News",
            content="Content",
            author=self.user,
            category=self.category,
            status=News.PUBLISHED,
            publish_date=timezone.now() + timezone.timedelta(days=10),
        )
        news.save()
        self.assertLessEqual(news.publish_date, timezone.now())

    def test_future_publish_date_reset_to_now_on_first_publish(self):
        """Test a brand new PUBLISHED item with a future publish_date gets reset to now"""
        future_date = timezone.now() + timezone.timedelta(days=30)
        news = News.objects.create(
            title="Future Dated News",
            content="Content",
            author=self.user,
            category=self.category,
            status=News.PUBLISHED,
            publish_date=future_date,
        )
        self.assertLess(news.publish_date, future_date)

    def test_auto_publish_date_on_status_change(self):
        """Test that publish_date is auto-set when status changes to PUBLISHED"""
        # Create draft news
        news = News.objects.create(
            title="Draft News",
            content="Content",
            author=self.user,
            category=self.category,
            status=News.DRAFT,
        )

        # publish_date should not be set or be in future for drafts
        news.publish_date

        # Change status to published
        news.status = News.PUBLISHED
        news.save()

        # publish_date should now be set to current time
        self.assertIsNotNone(news.publish_date)
        self.assertLessEqual(
            news.publish_date, timezone.now() + timezone.timedelta(seconds=1)
        )


class NewsFormEventDateValidationTests(TestCase):
    """NewsForm must reject an event ending before it starts"""

    def setUp(self):
        self.event_category, _ = NewsCategory.objects.get_or_create(
            name=NewsCategory.EVENT
        )

    def _base_data(self, **overrides):
        data = {
            "title": "Some Event",
            "category": self.event_category.pk,
            "content": "Content",
            "excerpt": "",
            "event_date": "2026-06-10T10:00",
            "event_end_date": "2026-06-12T10:00",
            "event_location": "Praça Central",
            "status": News.DRAFT,
        }
        data.update(overrides)
        return data

    def test_valid_event_dates_pass(self):
        form = NewsForm(data=self._base_data())
        self.assertTrue(form.is_valid(), form.errors)

    def test_event_end_date_before_start_date_is_invalid(self):
        form = NewsForm(
            data=self._base_data(
                event_date="2026-06-12T10:00",
                event_end_date="2026-06-10T10:00",
            )
        )
        self.assertFalse(form.is_valid())
        self.assertIn("event_end_date", form.errors)


class NewsListViewTests(TestCase):
    """Test suite for news list view"""

    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.url = reverse("news:news_list")
        self.user = User.objects.create_user(
            username="testauthor", password="testpass123"
        )
        self.category, _ = NewsCategory.objects.get_or_create(name=NewsCategory.NEWS)

        # Create published news
        self.published_news = News.objects.create(
            title="Published News",
            content="Published content",
            author=self.user,
            category=self.category,
            publish_date=timezone.now(),
            status=News.PUBLISHED,
        )

        # Create draft news (should not appear)
        self.draft_news = News.objects.create(
            title="Draft News",
            content="Draft content",
            author=self.user,
            category=self.category,
            publish_date=timezone.now(),
            status=News.DRAFT,
        )

    def test_news_list_page_loads(self):
        """Test that news list page loads successfully"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "news/news_list.html")

    def test_news_list_shows_published_only(self):
        """Test that only published news are shown"""
        response = self.client.get(self.url)
        self.assertContains(response, "Published News")
        self.assertNotContains(response, "Draft News")

    def test_news_list_filters_by_category(self):
        """Test the category query param filters the news list"""
        event_category, _ = NewsCategory.objects.get_or_create(name=NewsCategory.EVENT)
        News.objects.create(
            title="Event Item",
            content="Content",
            author=self.user,
            category=event_category,
            publish_date=timezone.now(),
            status=News.PUBLISHED,
        )
        response = self.client.get(self.url + f"?category={NewsCategory.NEWS}")
        titles = {n.title for n in response.context["news_items"]}
        self.assertEqual(titles, {"Published News"})

    def test_news_list_ordered_by_date(self):
        """Test that news are ordered by publish date (newest first)"""
        # Create older news
        older_news = News.objects.create(
            title="Older News",
            content="Content",
            author=self.user,
            category=self.category,
            publish_date=timezone.now() - timezone.timedelta(days=5),
            status=News.PUBLISHED,
        )

        response = self.client.get(self.url)
        news_items = list(response.context["news_items"])

        # Newest should be first
        self.assertEqual(news_items[0].title, "Published News")
        self.assertEqual(news_items[1].title, "Older News")


class NewsDetailViewTests(TestCase):
    """Test suite for news detail view"""

    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.user = User.objects.create_user(username="testauthor")
        self.category, _ = NewsCategory.objects.get_or_create(name=NewsCategory.NEWS)

        self.news = News.objects.create(
            title="Test News Article",
            slug="test-news-article",
            content="This is the full content of the news article",
            excerpt="This is a short excerpt",
            author=self.user,
            category=self.category,
            publish_date=timezone.now(),
            status=News.PUBLISHED,
        )
        self.url = reverse("news:news_detail", kwargs={"slug": self.news.slug})

    def test_news_detail_page_loads(self):
        """Test that news detail page loads successfully"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "news/news_detail.html")

    def test_news_detail_shows_content(self):
        """Test that news detail page shows full content"""
        response = self.client.get(self.url)
        self.assertContains(response, "Test News Article")
        self.assertContains(response, "This is the full content")

    def test_news_detail_shows_author(self):
        """Test that news detail page shows author"""
        response = self.client.get(self.url)
        self.assertContains(response, "testauthor")

    def test_news_detail_increments_view_count(self):
        """Test that viewing news increments view count"""
        initial_count = self.news.view_count
        self.client.get(self.url)

        # Refresh from database
        self.news.refresh_from_db()
        self.assertEqual(self.news.view_count, initial_count + 1)

    def test_news_detail_404_for_invalid_slug(self):
        """Test that invalid slug returns 404"""
        response = self.client.get(
            reverse("news:news_detail", kwargs={"slug": "non-existent"})
        )
        self.assertEqual(response.status_code, 404)


class NewsFeaturedTests(TestCase):
    """Test suite for featured news functionality"""

    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.user = User.objects.create_user(username="testauthor")
        self.category, _ = NewsCategory.objects.get_or_create(name=NewsCategory.NEWS)

    def test_featured_news_appears_in_context(self):
        """Test that featured news are available in context"""
        # Create featured news
        featured_news = News.objects.create(
            title="Featured News",
            content="Content",
            author=self.user,
            category=self.category,
            publish_date=timezone.now(),
            status=News.PUBLISHED,
            is_featured=True,
        )

        response = self.client.get(reverse("news:news_list"))

        # Featured items should be in context
        self.assertIn("featured_items", response.context)
        featured_items = list(response.context["featured_items"])

        # Should contain our featured news
        self.assertEqual(len(featured_items), 1)
        self.assertEqual(featured_items[0].title, "Featured News")


class NewsEventPropertyTests(TestCase):
    """Tests for is_upcoming_event/is_past_event on event and non-event news"""

    def setUp(self):
        self.user = User.objects.create_user(username="author", password="pass123")
        self.news_category, _ = NewsCategory.objects.get_or_create(
            name=NewsCategory.NEWS
        )
        self.event_category, _ = NewsCategory.objects.get_or_create(
            name=NewsCategory.EVENT
        )

    def test_non_event_is_never_upcoming_or_past(self):
        """Test regular news items are neither upcoming nor past events"""
        article = News.objects.create(
            title="Regular Article",
            content="Content",
            author=self.user,
            category=self.news_category,
            event_date=timezone.now() + timezone.timedelta(days=1),
        )
        self.assertFalse(article.is_upcoming_event)
        self.assertFalse(article.is_past_event)

    def test_event_without_date_is_neither(self):
        """Test an event with no event_date is treated as neither upcoming nor past"""
        event = News.objects.create(
            title="Dateless Event",
            content="Content",
            author=self.user,
            category=self.event_category,
        )
        self.assertFalse(event.is_upcoming_event)
        self.assertFalse(event.is_past_event)

    def test_future_event_is_upcoming(self):
        """Test an event with a future date is upcoming, not past"""
        event = News.objects.create(
            title="Future Event",
            content="Content",
            author=self.user,
            category=self.event_category,
            event_date=timezone.now() + timezone.timedelta(days=5),
        )
        self.assertTrue(event.is_upcoming_event)
        self.assertFalse(event.is_past_event)

    def test_past_event_is_past(self):
        """Test an event with a past date is past, not upcoming"""
        event = News.objects.create(
            title="Past Event",
            content="Content",
            author=self.user,
            category=self.event_category,
            event_date=timezone.now() - timezone.timedelta(days=5),
        )
        self.assertFalse(event.is_upcoming_event)
        self.assertTrue(event.is_past_event)


class NewsExcerptAutoGenerationTests(TestCase):
    """Tests for automatic excerpt generation on save"""

    def setUp(self):
        self.user = User.objects.create_user(username="author", password="pass123")
        self.category, _ = NewsCategory.objects.get_or_create(name=NewsCategory.NEWS)

    def test_short_content_used_as_excerpt_verbatim(self):
        """Test content under 300 chars becomes the excerpt unchanged"""
        news = News.objects.create(
            title="Short",
            content="A short piece of content.",
            author=self.user,
            category=self.category,
        )
        self.assertEqual(news.excerpt, "A short piece of content.")

    def test_long_content_is_truncated_for_excerpt(self):
        """Test content over 300 chars is truncated to 297 chars plus ellipsis"""
        long_content = "A" * 400
        news = News.objects.create(
            title="Long",
            content=long_content,
            author=self.user,
            category=self.category,
        )
        self.assertEqual(len(news.excerpt), 300)
        self.assertTrue(news.excerpt.endswith("..."))

    def test_explicit_excerpt_is_not_overwritten(self):
        """Test a manually provided excerpt is preserved"""
        news = News.objects.create(
            title="Custom Excerpt",
            content="A" * 400,
            excerpt="My own summary",
            author=self.user,
            category=self.category,
        )
        self.assertEqual(news.excerpt, "My own summary")


class NewsFormValidationTests(TestCase):
    """Tests for NewsForm field validation beyond event date ordering"""

    def setUp(self):
        self.event_category, _ = NewsCategory.objects.get_or_create(
            name=NewsCategory.EVENT
        )
        self.news_category, _ = NewsCategory.objects.get_or_create(
            name=NewsCategory.NEWS
        )

    def test_event_without_date_is_invalid(self):
        """Test event category requires an event_date"""
        form = NewsForm(
            data={
                "title": "Some Event",
                "category": self.event_category.pk,
                "content": "Content",
                "excerpt": "",
                "event_location": "Praça Central",
                "status": News.DRAFT,
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("event_date", form.errors)

    def test_event_without_location_is_invalid(self):
        """Test event category requires an event_location"""
        form = NewsForm(
            data={
                "title": "Some Event",
                "category": self.event_category.pk,
                "content": "Content",
                "excerpt": "",
                "event_date": "2026-06-10T10:00",
                "status": News.DRAFT,
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("event_location", form.errors)

    def test_regular_news_does_not_require_event_fields(self):
        """Test non-event categories don't require event_date/location"""
        form = NewsForm(
            data={
                "title": "Regular News",
                "category": self.news_category.pk,
                "content": "Content",
                "excerpt": "",
                "status": News.DRAFT,
            }
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_excerpt_over_300_chars_is_invalid(self):
        """Test an explicit excerpt longer than 300 chars is rejected"""
        form = NewsForm(
            data={
                "title": "Long Excerpt",
                "category": self.news_category.pk,
                "content": "Content",
                "excerpt": "A" * 301,
                "status": News.DRAFT,
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("excerpt", form.errors)


class NewsAdminTests(TestCase):
    """Tests for NewsAdmin.save_model author assignment"""

    def setUp(self):
        self.factory = RequestFactory()
        self.staff_user = User.objects.create_user(
            username="staffuser", password="pass123", is_staff=True
        )
        self.other_staff = User.objects.create_user(
            username="otherstaff", password="pass123", is_staff=True
        )
        self.category, _ = NewsCategory.objects.get_or_create(name=NewsCategory.NEWS)

    def test_save_model_sets_author_on_create(self):
        """Test creating a News via admin sets author to the current request user"""
        news_admin = admin.site._registry[News]
        request = self.factory.post("/admin/news/news/add/")
        request.user = self.staff_user

        news = News(title="Admin Created", content="Content", category=self.category)
        news_admin.save_model(request, news, form=None, change=False)

        self.assertEqual(news.author, self.staff_user)

    def test_save_model_does_not_override_author_on_change(self):
        """Test editing an existing News via admin keeps the original author"""
        news = News.objects.create(
            title="Existing",
            content="Content",
            author=self.staff_user,
            category=self.category,
        )
        news_admin = admin.site._registry[News]
        request = self.factory.post(f"/admin/news/news/{news.pk}/change/")
        request.user = self.other_staff

        news_admin.save_model(request, news, form=None, change=True)

        self.assertEqual(news.author, self.staff_user)


class NewsListSortingTests(TestCase):
    """Tests for news list sorting options and upcoming events"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="author", password="pass123")
        self.category, _ = NewsCategory.objects.get_or_create(name=NewsCategory.NEWS)
        self.event_category, _ = NewsCategory.objects.get_or_create(
            name=NewsCategory.EVENT
        )
        self.url = reverse("news:news_list")

        self.older = News.objects.create(
            title="Older News",
            content="Content",
            author=self.user,
            category=self.category,
            status=News.PUBLISHED,
            publish_date=timezone.now() - timezone.timedelta(days=3),
            view_count=1,
        )
        self.newer = News.objects.create(
            title="Newer News",
            content="Content",
            author=self.user,
            category=self.category,
            status=News.PUBLISHED,
            publish_date=timezone.now(),
            view_count=10,
        )

    def test_sort_oldest_orders_ascending_by_date(self):
        """Test 'oldest' sort orders publish_date ascending"""
        response = self.client.get(self.url + "?sort=oldest")
        items = list(response.context["news_items"])
        self.assertEqual(items[0], self.older)
        self.assertEqual(items[1], self.newer)

    def test_sort_popular_orders_by_view_count(self):
        """Test 'popular' sort orders by view_count descending"""
        response = self.client.get(self.url + "?sort=popular")
        items = list(response.context["news_items"])
        self.assertEqual(items[0], self.newer)

    def test_upcoming_events_appear_in_context(self):
        """Test upcoming events are surfaced separately in context"""
        upcoming = News.objects.create(
            title="Upcoming Event",
            content="Content",
            author=self.user,
            category=self.event_category,
            status=News.PUBLISHED,
            publish_date=timezone.now(),
            event_date=timezone.now() + timezone.timedelta(days=2),
        )
        response = self.client.get(self.url)
        upcoming_events = list(response.context["upcoming_events"])
        self.assertIn(upcoming, upcoming_events)


class NewsImporterTests(TestCase):
    """Importer reads a saved feed; no network access"""

    FEED = Path(__file__).parent / "testdata" / "feed_sample.xml"
    NOW = datetime(2026, 10, 10, 12, 0, tzinfo=dt_timezone.utc)

    def _import(self, **kwargs):
        items = importer.parse_feed(self.FEED.read_bytes())
        options = {"days": 30, "limit": 40, "now": self.NOW}
        options.update(kwargs)
        return importer.import_items(items, **options)

    def test_parse_strips_source_suffix_and_skips_invalid_items(self):
        items = importer.parse_feed(self.FEED.read_bytes())
        urls = {item.source_url for item in items}
        self.assertNotIn("http://example.com/insecure", urls)
        self.assertNotIn("https://example.com/nodate", urls)
        first = next(i for i in items if i.source_url == "https://example.com/a")
        self.assertEqual(first.title, "Maricá inaugura nova ciclovia na orla")
        self.assertEqual(first.source_name, "Jornal A")

    def test_import_keeps_only_recent_relevant_items(self):
        self.assertEqual(self._import(), 2)
        imported = News.objects.exclude(source_url="")
        self.assertEqual(
            set(imported.values_list("source_url", flat=True)),
            {"https://example.com/a", "https://example.com/b"},
        )
        item = imported.get(source_url="https://example.com/a")
        self.assertEqual(item.status, News.PUBLISHED)
        self.assertEqual(
            item.publish_date, datetime(2026, 10, 8, 14, 0, tzinfo=dt_timezone.utc)
        )
        self.assertTrue(item.is_external)
        self.assertFalse(item.author.is_active)

    def test_import_is_idempotent(self):
        self._import()
        self.assertEqual(self._import(), 0)
        self.assertEqual(News.objects.exclude(source_url="").count(), 2)

    def test_import_respects_limit(self):
        self.assertEqual(self._import(limit=1), 1)

    def test_purge_removes_only_imported_items(self):
        author = User.objects.create_user(username="editor", password="pass123")
        category, _ = NewsCategory.objects.get_or_create(name=NewsCategory.NEWS)
        News.objects.create(
            title="Manual", content="c", category=category, author=author
        )
        self._import()
        self.assertEqual(importer.purge_imported(), 2)
        self.assertEqual(News.objects.count(), 1)

    def test_command_imports_from_file_and_purges(self):
        out = StringIO()
        call_command("fetch_news", file=str(self.FEED), days=36500, stdout=out)
        self.assertIn("importada", out.getvalue())
        self.assertTrue(News.objects.exclude(source_url="").exists())
        call_command("fetch_news", purge=True, stdout=out)
        self.assertFalse(News.objects.exclude(source_url="").exists())

    def test_fetch_feed_rejects_non_https(self):
        with self.assertRaises(ValueError):
            importer.fetch_feed("http://example.com/feed")

    def test_build_feed_url_uses_setting_override(self):
        with self.settings(
            NEWS_FEED_URL="https://proxy.example/feed?q={query}&d={days}"
        ):
            url = importer.build_feed_url("Maricá RJ", 7)
        self.assertEqual(url, "https://proxy.example/feed?q=Maric%C3%A1+RJ&d=7")


class NewsListLayoutTests(TestCase):
    """Own content is listed before imported headlines; empty tabs are hidden"""

    def setUp(self):
        self.author = User.objects.create_user(username="editor2", password="pass123")
        self.category, _ = NewsCategory.objects.get_or_create(name=NewsCategory.NEWS)
        News.objects.create(
            title="Matéria própria antiga",
            content="c",
            category=self.category,
            author=self.author,
            status=News.PUBLISHED,
            publish_date=timezone.now() - timezone.timedelta(days=90),
        )
        News.objects.create(
            title="Manchete externa recente",
            content="c",
            category=self.category,
            author=self.author,
            status=News.PUBLISHED,
            publish_date=timezone.now() - timezone.timedelta(days=1),
            source_name="Jornal X",
            source_url="https://example.com/x",
        )

    def test_own_items_come_before_press_items(self):
        response = self.client.get(reverse("news:news_list"))
        titles = [n.title for n in response.context["news_items"]]
        self.assertEqual(titles, ["Matéria própria antiga", "Manchete externa recente"])
        self.assertEqual(len(response.context["own_items"]), 1)
        self.assertEqual(len(response.context["press_items"]), 1)
        self.assertContains(response, "Na imprensa")

    def test_empty_category_tab_is_hidden(self):
        NewsCategory.objects.get_or_create(name=NewsCategory.ANNOUNCEMENT)
        response = self.client.get(reverse("news:news_list"))
        self.assertNotContains(response, "?category=Anuncios")


class AgendaTests(TestCase):
    """The events page leads with upcoming and ongoing events"""

    def setUp(self):
        self.author = User.objects.create_user(username="agenda", password="pass123")
        self.events, _ = NewsCategory.objects.get_or_create(name=NewsCategory.EVENT)
        now = timezone.now()
        self.ongoing = self._event("Festival em andamento", now - timedelta(days=1))
        self.ongoing.event_end_date = now + timedelta(days=2)
        self.ongoing.save()
        self.later = self._event("Show daqui a uma semana", now + timedelta(days=7))
        self.past = self._event("Feira encerrada", now - timedelta(days=30))

    def _event(self, title, when):
        return News.objects.create(
            title=title,
            content="c",
            category=self.events,
            author=self.author,
            status=News.PUBLISHED,
            publish_date=timezone.now() - timedelta(days=40),
            event_date=when,
            event_location="Orla",
        )

    def test_upcoming_events_include_ongoing_in_date_order(self):
        self.assertEqual(
            list(News.objects.published().upcoming_events()),
            [self.ongoing, self.later],
        )

    def test_ongoing_event_is_not_past(self):
        self.assertTrue(self.ongoing.is_ongoing_event)
        self.assertFalse(self.ongoing.is_past_event)

    def test_agenda_leads_and_is_not_repeated_below(self):
        response = self.client.get(reverse("news:news_list"))
        self.assertEqual(response.context["agenda"], [self.ongoing, self.later])
        self.assertEqual(list(response.context["news_items"]), [self.past])
        self.assertContains(response, "Acontecendo agora")

    def test_landing_shows_only_upcoming_events(self):
        response = self.client.get(reverse("core:landing"))
        self.assertContains(response, "Próximos eventos em Maricá")
        self.assertContains(response, "Show daqui a uma semana")
        self.assertNotContains(response, "Feira encerrada")


class EventCrawlerTests(TestCase):
    """Crawler reads a saved API response; no network access"""

    POSTS = Path(__file__).parent / "testdata" / "prefeitura_posts.json"
    NOW = datetime(2026, 10, 21, 12, 0, tzinfo=dt_timezone.utc)

    def setUp(self):
        self.posts = event_crawler.parse_prefeitura_posts(self.POSTS.read_bytes())
        self.moderator = User.objects.create_user(
            username="mod", password="pass123", is_staff=True
        )

    def _store(self):
        return event_crawler.store_candidates(self.posts, now=self.NOW)

    def test_parse_skips_non_https_and_strips_html(self):
        self.assertEqual([p.source_id for p in self.posts], ["101", "102", "103"])
        self.assertEqual(self.posts[0].title, "Maricá terá festival de música na orla")
        self.assertNotIn("<p>", self.posts[0].text)

    def test_extracts_range_time_and_location(self):
        found = event_crawler.extract(self.posts[0])
        local = timezone.localtime(found.start)
        self.assertEqual((local.day, local.month, local.hour), (30, 10, 16))
        self.assertEqual(timezone.localtime(found.end).date().isoformat(), "2026-11-08")
        self.assertEqual(found.location, "Orla do Parque Nanci")

    def test_extracts_numeric_date_and_neighbourhood(self):
        found = event_crawler.extract(self.posts[1])
        local = timezone.localtime(found.start)
        self.assertEqual((local.day, local.month, local.hour), (27, 10, 18))
        self.assertEqual(found.location, "Praça Orlando de Barros Pimentel, Centro")

    def test_only_upcoming_announcements_become_candidates(self):
        self.assertEqual(self._store(), 2)
        self.assertEqual(
            set(EventCandidate.objects.values_list("source_id", flat=True)),
            {"101", "102"},
        )

    def test_store_is_idempotent(self):
        self._store()
        self.assertEqual(self._store(), 0)

    def test_flags_possible_duplicate_of_published_event(self):
        category, _ = NewsCategory.objects.get_or_create(name=NewsCategory.EVENT)
        existing = News.objects.create(
            title="Maricá terá festival de música na Orla",
            content="c",
            category=category,
            author=self.moderator,
            status=News.PUBLISHED,
            event_date=datetime(2026, 10, 30, 19, 0, tzinfo=dt_timezone.utc),
            event_location="Orla",
        )
        self._store()
        candidate = EventCandidate.objects.get(source_id="101")
        self.assertEqual(candidate.possible_duplicate, existing)

    def test_approve_publishes_event_with_image_and_source(self):
        self._store()
        candidate = EventCandidate.objects.get(source_id="101")
        news = event_crawler.approve(
            candidate, self.moderator, image_fetcher=lambda url: b"fake-image"
        )
        self.assertTrue(news.is_event)
        self.assertEqual(news.status, News.PUBLISHED)
        self.assertEqual(news.event_location, "Orla do Parque Nanci")
        self.assertFalse(news.is_external)
        self.assertTrue(news.featured_image.name.endswith(".jpg"))
        candidate.refresh_from_db()
        self.assertEqual(candidate.status, EventCandidate.APPROVED)
        self.assertEqual(candidate.news, news)
        news.featured_image.delete(save=False)

    def test_purge_keeps_crawled_events(self):
        self._store()
        event_crawler.approve(
            EventCandidate.objects.get(source_id="102"),
            self.moderator,
            image_fetcher=lambda url: None,
        )
        importer.purge_imported()
        self.assertTrue(News.objects.filter(source_url__contains="pedalada").exists())


class EventTriageViewTests(TestCase):
    def setUp(self):
        self.moderator = User.objects.create_user(
            username="mod", password="pass123", is_staff=True
        )
        self.candidate = EventCandidate.objects.create(
            source="prefeitura",
            source_id="1",
            source_name="Prefeitura de Maricá",
            source_url="https://www.marica.rj.gov.br/noticia/x/",
            source_published_at=timezone.now(),
            title="Show na praça",
            summary="Descrição do show.",
            event_date=timezone.now() + timedelta(days=5),
        )
        self.url = reverse("core:admin_event_triage_action", args=[self.candidate.pk])

    def _post(self, **extra):
        data = {
            "c1-title": "Show na praça",
            "c1-summary": "Descrição do show.",
            "c1-event_date": (timezone.now() + timedelta(days=5)).strftime(
                "%Y-%m-%dT%H:%M"
            ),
            "c1-event_end_date": "",
            "c1-event_location": "Praça Central",
            "action": "approve",
        }
        data.update(extra)
        return self.client.post(self.url, data)

    def test_regular_user_cannot_triage(self):
        User.objects.create_user(username="visitor", password="pass123")
        self.client.login(username="visitor", password="pass123")
        self._post()
        self.candidate.refresh_from_db()
        self.assertEqual(self.candidate.status, EventCandidate.PENDING)

    def test_approve_requires_location(self):
        self.client.login(username="mod", password="pass123")
        response = self._post(**{"c1-event_location": ""})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(News.objects.exists())

    def test_approve_publishes_on_agenda(self):
        self.client.login(username="mod", password="pass123")
        self._post()
        news = News.objects.get()
        self.assertEqual(news.event_location, "Praça Central")
        response = self.client.get(reverse("news:news_list"))
        self.assertIn(news, response.context["agenda"])

    def test_reject(self):
        self.client.login(username="mod", password="pass123")
        self._post(action="reject")
        self.candidate.refresh_from_db()
        self.assertEqual(self.candidate.status, EventCandidate.REJECTED)


class EventWhenFilterTests(TestCase):
    """Event dates read naturally in each language"""

    def setUp(self):
        author = User.objects.create_user(username="dates", password="pass123")
        category, _ = NewsCategory.objects.get_or_create(name=NewsCategory.EVENT)
        tz = timezone.get_current_timezone()
        self.event = News(
            title="FLIM",
            category=category,
            author=author,
            event_date=datetime(2026, 10, 30, tzinfo=tz),
            event_end_date=datetime(2026, 11, 8, 23, 59, tzinfo=tz),
        )

    def _when(self, lang):
        from django.utils import translation

        from apps.news.templatetags.event_dates import event_when

        with translation.override(lang):
            return event_when(self.event)

    def test_range_across_months(self):
        self.assertEqual(self._when("pt-br"), "30 de outubro a 8 de novembro")
        self.assertEqual(self._when("en"), "October 30 – November 8")
        self.assertEqual(self._when("es"), "30 de octubre al 8 de noviembre")

    def test_range_within_a_month(self):
        self.event.event_date = self.event.event_date.replace(day=26)
        self.event.event_end_date = self.event.event_end_date.replace(month=10, day=27)
        self.assertEqual(self._when("pt-br"), "26 a 27 de outubro")
        self.assertEqual(self._when("en"), "October 26–27")

    def test_calendar_and_maps_links(self):
        self.event.event_location = "Orla do Parque Nanci"
        self.assertIn("calendar.google.com", self.event.calendar_url)
        self.assertIn("20261030T030000Z", self.event.calendar_url)
        self.assertIn("Orla+do+Parque+Nanci", self.event.maps_url)
