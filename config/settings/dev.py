"""
Development settings.

Loaded by default (see manage.py / config/wsgi.py / config/asgi.py) unless
DJANGO_SETTINGS_MODULE is explicitly set to config.settings.prod. Optimized
for a friendly local dev/test loop: DEBUG on by default, permissive hosts,
no HTTPS-only cookies/redirects (which would break plain http://localhost).
"""

from decouple import config

from .base import *  # noqa: F401,F403
from .base import LOGGING

# DEBUG defaults to True here (base.py defaults to False) so `runserver`
# and the test suite behave sensibly even if DEBUG isn't set in .env at all.
DEBUG = config("DEBUG", default=True, cast=bool)

# Permissive host/CSRF-trusted-origin defaults for local development, so
# runserver, Docker port-forwarding, etc. all "just work" without extra
# .env configuration. Still overridable via ALLOWED_HOSTS if needed.
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1,0.0.0.0").split(
    ","
)

# Verbose console logging in dev for the app's own code. Django's own
# "django" logger is deliberately left at base.py's INFO level rather than
# DEBUG - Django's internals (e.g. django.template) log every non-fatal
# template variable lookup miss at DEBUG, which floods the console/test
# output without being actionable.
LOGGING["root"]["level"] = "DEBUG"
LOGGING["loggers"]["apps"]["level"] = "DEBUG"
