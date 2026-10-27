"""Development settings. Loaded by default unless DJANGO_SETTINGS_MODULE=config.settings.prod."""

from decouple import config

from .base import *  # noqa: F401,F403
from .base import INSTALLED_APPS, LOGGING

DEBUG = config("DEBUG", default=True, cast=bool)

ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1,0.0.0.0").split(
    ","
)

# Whitenoise serves static files in dev too. CSS/JS are not cached, so edits show up
# on a normal reload; images and fonts are cached for a day, otherwise every page
# change revalidates each one and they flash empty until the server answers.
INSTALLED_APPS = ["whitenoise.runserver_nostatic", *INSTALLED_APPS]
WHITENOISE_USE_FINDERS = True
WHITENOISE_AUTOREFRESH = True
WHITENOISE_MAX_AGE = 0

_CACHED_STATIC = (".webp", ".jpg", ".jpeg", ".png", ".svg", ".ico", ".woff2", ".woff")


def _static_headers(headers, path, url):
    if path.lower().endswith(_CACHED_STATIC):
        headers["Cache-Control"] = "public, max-age=86400"


WHITENOISE_ADD_HEADERS_FUNCTION = _static_headers

LOGGING["root"]["level"] = "DEBUG"
LOGGING["loggers"]["apps"]["level"] = "DEBUG"
