"""Development settings. Loaded by default unless DJANGO_SETTINGS_MODULE=config.settings.prod."""

from decouple import Csv, config

from .base import *  # noqa: F401,F403
from .base import INSTALLED_APPS, LOGGING

DEBUG = config("DEBUG", default=True, cast=bool)

ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1,0.0.0.0").split(
    ","
)

# Static files work like production: versioned URLs (config/storage.py) cached for a
# year, so pages never revalidate CSS, JS or images; an edit changes the URL.
INSTALLED_APPS = ["whitenoise.runserver_nostatic", *INSTALLED_APPS]
WHITENOISE_USE_FINDERS = True
WHITENOISE_AUTOREFRESH = True
WHITENOISE_MAX_AGE = 60 * 60 * 24 * 365


def _versioned(path, url):
    # Every static URL carries ?v=<mtime> (see config/storage.py)
    return True


WHITENOISE_IMMUTABLE_FILE_TEST = _versioned
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "config.storage.VersionedStaticFilesStorage"},
}

# Testes manuais: as telas de código já vêm preenchidas com o que chegou ao MailHog
EMAIL_CODE_AUTOFILL = (
    "mailhog" if config("EMAIL_CODE_AUTOFILL", default=DEBUG, cast=bool) else ""
)
EMAIL_CODE_AUTOFILL_DOMAINS = config(
    "EMAIL_CODE_AUTOFILL_DOMAINS", default="*", cast=Csv()
)
MAILHOG_API_URL = config("MAILHOG_API_URL", default="http://localhost:8025")

LOGGING["root"]["level"] = "DEBUG"
LOGGING["loggers"]["apps"]["level"] = "DEBUG"
