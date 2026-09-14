from django.contrib import admin
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.news.forms import NewsForm
from apps.news.models import News, NewsCategory


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
