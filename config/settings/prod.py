"""
Production settings.

Activated by explicitly setting DJANGO_SETTINGS_MODULE=config.settings.prod
in the deployment environment (dev.py is the default everywhere else,
including CI). Adds the production security hardening flagged by Django's
`manage.py check --deploy` and expected when the app sits behind a reverse
proxy / CDN (e.g. Cloudflare).

Most of the security toggles below are themselves controlled by env vars,
defaulting to "secure" in prod but easy to relax for a staging environment
that isn't served over HTTPS yet.
"""

from decouple import config

from .base import *  # noqa: F401,F403
from .base import LOGGING

DEBUG = config("DEBUG", default=False, cast=bool)

# In production ALLOWED_HOSTS must be set explicitly to the real domain(s) -
# no permissive default here.
ALLOWED_HOSTS = config("ALLOWED_HOSTS").split(",")

# --- Reverse proxy / CDN (e.g. Cloudflare) awareness -----------------------
# The origin server sits behind a proxy that terminates TLS, so Django only
# ever sees plain HTTP internally. This header tells Django to trust the
# proxy's X-Forwarded-Proto header when deciding if the original request
# was HTTPS (used by SECURE_SSL_REDIRECT and request.is_secure()).
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# --- HTTPS enforcement & secure cookies -------------------------------------
# Default to "on" in prod, but each stays overridable via env so a staging
# deployment without HTTPS yet (or CI running with prod settings) doesn't
# get forced into a redirect loop / broken cookies.
SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=True, cast=bool)
SESSION_COOKIE_SECURE = config("SESSION_COOKIE_SECURE", default=True, cast=bool)
CSRF_COOKIE_SECURE = config("CSRF_COOKIE_SECURE", default=True, cast=bool)

# --- HSTS --------------------------------------------------------------------
# Defaults to a conservative but meaningful 1 day. Ramp this up (e.g. to
# 31536000 for a full year) once HTTPS is confirmed stable in production,
# per Django's deployment checklist.
SECURE_HSTS_SECONDS = config("SECURE_HSTS_SECONDS", default=86400, cast=int)
SECURE_HSTS_INCLUDE_SUBDOMAINS = config(
    "SECURE_HSTS_INCLUDE_SUBDOMAINS", default=True, cast=bool
)
SECURE_HSTS_PRELOAD = config("SECURE_HSTS_PRELOAD", default=True, cast=bool)

# --- Misc hardening ----------------------------------------------------------
SECURE_CONTENT_TYPE_NOSNIFF = config(
    "SECURE_CONTENT_TYPE_NOSNIFF", default=True, cast=bool
)

# --- Logging -------------------------------------------------------------
# Structured (key=value) console output for container log collectors, at a
# quieter level than dev since prod doesn't need per-request debug noise.
for _handler in LOGGING["handlers"].values():
    _handler["formatter"] = "structured"
LOGGING["root"]["level"] = "INFO"
LOGGING["loggers"]["django"]["level"] = "INFO"
LOGGING["loggers"]["django.request"]["level"] = "ERROR"
LOGGING["loggers"]["apps"]["level"] = "INFO"
