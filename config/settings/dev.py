"""Development settings. Loaded by default unless DJANGO_SETTINGS_MODULE=config.settings.prod."""

from decouple import config

from .base import *  # noqa: F401,F403
from .base import LOGGING

DEBUG = config("DEBUG", default=True, cast=bool)

ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1,0.0.0.0").split(
    ","
)

LOGGING["root"]["level"] = "DEBUG"
LOGGING["loggers"]["apps"]["level"] = "DEBUG"
