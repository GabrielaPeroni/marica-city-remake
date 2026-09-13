from pathlib import Path

from decouple import config

# config/settings/base.py -> config/settings/ -> config/ -> repo root
BASE_DIR = Path(__file__).resolve().parent.parent.parent
SECRET_KEY = config("SECRET_KEY")

# DEBUG and ALLOWED_HOSTS have sensible shared defaults here, but are
# re-declared explicitly in dev.py / prod.py so each environment's intent
# is obvious without having to cross-reference this file.
DEBUG = config("DEBUG", default=False, cast=bool)

ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Aplicativos
    "django_ratelimit",
    "apps.core",
    "apps.accounts",
    "apps.explore",
    "apps.news",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.google_oauth",
                "apps.core.context_processors.admin_stats",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": config("DB_ENGINE", default="django.db.backends.sqlite3"),
        "NAME": config("DB_NAME", default=str(BASE_DIR / "db.sqlite3")),
        "USER": config("DB_USER", default=""),
        "PASSWORD": config("DB_PASSWORD", default=""),
        "HOST": config("DB_HOST", default=""),
        "PORT": config("DB_PORT", default=""),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True

# Cache backend (also used for django-ratelimit, see RATELIMIT_USE_CACHE below).
#
# Configurable via env so prod can point at Redis without code changes:
#   CACHE_URL=rediss://:password@host:6379/0   (or REDIS_URL, checked as a fallback)
# Leaving both unset keeps the LocMemCache default, which is fine for local
# dev/tests but is per-process and NOT safe for a multi-process/multi-worker
# production deployment (rate limiting and any other cached state would be
# inconsistent across workers).
_CACHE_URL = config("CACHE_URL", default=config("REDIS_URL", default=""))

if _CACHE_URL:
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": _CACHE_URL,
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
            },
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "ratelimit-cache",
        }
    }

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

# Arquivos de mídia (Conteúdo enviado pelo usuário)
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Modelo de Usuário Personalizado
AUTH_USER_MODEL = "accounts.User"

# Configurações de autenticação
# Redirecionar para a página inicial onde o modal de login está disponível
LOGIN_URL = "core:landing"
LOGIN_REDIRECT_URL = "core:landing"
LOGOUT_REDIRECT_URL = "core:landing"

# Configurações do Google
# Deve ser definido no arquivo .env
GOOGLE_OAUTH_CLIENT_ID = config("GOOGLE_OAUTH_CLIENT_ID")
GOOGLE_MAPS_API_KEY = config("GOOGLE_MAPS_API_KEY", default="")

# Limitação de Taxa (para prevenir abuso de API)
RATELIMIT_ENABLE = config("RATELIMIT_ENABLE", default=True, cast=bool)
RATELIMIT_USE_CACHE = "default"  # Usar cache padrão para limitação de taxa
RATELIMIT_VIEW = "apps.explore.ratelimit_handlers.ratelimited_error"

# Silenciar avisos do django-ratelimit para LocMemCache em desenvolvimento
# Quando CACHE_URL/REDIS_URL aponta para Redis (ex.: em produção), esses
# avisos não se aplicam, mas mantê-los silenciados também no LocMemCache
# de dev evita ruído desnecessário.
SILENCED_SYSTEM_CHECKS = ["django_ratelimit.E003", "django_ratelimit.W001"]

# Configuração de testes
# Usar executor de testes personalizado para excluir .github da descoberta de testes
TEST_RUNNER = "config.test_runner.CustomTestRunner"

# Logging
#
# Shared base: everything logs to the console (stdout/stderr), which is the
# right target for both `runserver` in dev and a containerized prod
# deployment (container log collectors — Docker, Cloudflare, any PaaS —
# expect app logs on stdout/stderr rather than files). dev.py and prod.py
# each set their own levels/formatter on top of this skeleton.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {
            "format": "[{levelname}] {asctime} {name}: {message}",
            "style": "{",
        },
        "structured": {
            # key=value style output that's easy for container log collectors
            # (Docker, Cloudflare, any PaaS log pipeline) to parse as
            # semi-structured text without needing a JSON logging library.
            "format": (
                'level={levelname} time="{asctime}" logger={name} message="{message}"'
            ),
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "apps": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
