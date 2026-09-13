import os

from django.core.asgi import get_asgi_application

# Defaults to dev settings; production sets DJANGO_SETTINGS_MODULE=
# config.settings.prod explicitly in its process environment.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

application = get_asgi_application()
