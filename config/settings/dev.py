"""Development settings. Loaded by default unless DJANGO_SETTINGS_MODULE=config.settings.prod."""

from decouple import config

from .base import *  # noqa: F401,F403
from .base import INSTALLED_APPS, LOGGING

DEBUG = config("DEBUG", default=True, cast=bool)

ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1,0.0.0.0").split(
    ","
)

# Whitenoise serves static files in dev too, with no browser caching, so
# CSS/JS edits show up on a normal reload.
INSTALLED_APPS = ["whitenoise.runserver_nostatic", *INSTALLED_APPS]
WHITENOISE_USE_FINDERS = True
WHITENOISE_AUTOREFRESH = True
WHITENOISE_MAX_AGE = 0

LOGGING["root"]["level"] = "DEBUG"
LOGGING["loggers"]["apps"]["level"] = "DEBUG"
