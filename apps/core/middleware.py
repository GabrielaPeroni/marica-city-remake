from django.urls import reverse

from apps.core.views import health_view


class HealthCheckMiddleware:
    """Answers /healthz/ before host validation and the HTTPS redirect.

    Probes from Docker, load balancers or the platform call the container
    directly (http://127.0.0.1:8000/healthz/), which ALLOWED_HOSTS and
    SECURE_SSL_REDIRECT would otherwise turn into a 400 or a 301.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.path = reverse("healthz")

    def __call__(self, request):
        if request.path == self.path:
            return health_view(request)
        return self.get_response(request)
