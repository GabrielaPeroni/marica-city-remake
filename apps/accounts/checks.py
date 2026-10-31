from django.conf import settings
from django.core.checks import Tags, Warning, register


@register(Tags.caches, deploy=True)
def code_cache_is_shared(app_configs, **kwargs):
    # Os códigos de e-mail ficam no cache; em serverless (Vercel) cada instância
    # tem seu próprio LocMemCache, então o código "some" entre requisições.
    backend = settings.CACHES["default"]["BACKEND"]
    if backend.endswith("LocMemCache"):
        return [
            Warning(
                "E-mail codes are stored in a per-process LocMemCache.",
                hint="Set CACHE_URL/REDIS_URL (e.g. Upstash Redis) in deployments.",
                id="accounts.W001",
            )
        ]
    return []
